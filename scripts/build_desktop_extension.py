"""Build and inspect the Claude Desktop MCP Bundle with the official CLI."""

from __future__ import annotations

import argparse
import hashlib
import stat
import subprocess
import sys
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Protocol

from scripts.check_desktop_extension import validate_desktop_extension

MCPB_CLI_PACKAGE = "@anthropic-ai/mcpb@2.1.2"
_MAX_UNCOMPRESSED_BYTES = 5 * 1024 * 1024
_REQUIRED_ARCHIVE_FILES = {
    "README.md",
    "icon.png",
    "manifest.json",
    "pyproject.toml",
    "src/server.py",
}
_FORBIDDEN_FILENAMES = {".env", "id_rsa", "id_ed25519"}
_FORBIDDEN_SUFFIXES = {".key", ".p12", ".pem"}


class CommandRunner(Protocol):
    """Callable boundary around the external MCPB CLI."""

    def __call__(self, command: Sequence[str], *, cwd: Path) -> None:
        """Run one CLI command from the repository root."""


@dataclass(frozen=True)
class DesktopExtensionBuildReport:
    """Verified metadata for a built MCPB artifact."""

    version: str
    artifact_path: Path
    sha256: str
    size_bytes: int
    files: tuple[str, ...]


@dataclass(frozen=True)
class DesktopExtensionArtifactReport:
    """Security-relevant archive properties captured after packing."""

    sha256: str
    size_bytes: int
    files: tuple[str, ...]


def build_desktop_extension(
    *,
    extension_root: Path = Path("desktop-extension"),
    pyproject_path: Path = Path("pyproject.toml"),
    output_dir: Path = Path("dist/mcpb"),
    command_runner: CommandRunner | None = None,
) -> DesktopExtensionBuildReport:
    """Validate, pack, and inspect a versioned MCPB artifact."""
    extension_root = extension_root.resolve()
    pyproject_path = pyproject_path.resolve()
    repository_root = pyproject_path.parent
    output_dir = output_dir.resolve()
    source_report = validate_desktop_extension(
        extension_root=extension_root,
        pyproject_path=pyproject_path,
    )
    artifact_path = output_dir / f"albumentationsx-mcp-{source_report.version}.mcpb"
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_path.unlink(missing_ok=True)

    runner = command_runner or _run_command
    validate_command = [
        "npx",
        "--yes",
        "--package",
        MCPB_CLI_PACKAGE,
        "mcpb",
        "validate",
        str(extension_root / "manifest.json"),
    ]
    pack_command = [
        "npx",
        "--yes",
        "--package",
        MCPB_CLI_PACKAGE,
        "mcpb",
        "pack",
        str(extension_root),
        str(artifact_path),
    ]

    runner(validate_command, cwd=repository_root)
    runner(pack_command, cwd=repository_root)
    try:
        artifact_report = inspect_desktop_extension_artifact(
            artifact_path=artifact_path,
            extension_root=extension_root,
        )
    except (OSError, ValueError, zipfile.BadZipFile):
        artifact_path.unlink(missing_ok=True)
        raise

    return DesktopExtensionBuildReport(
        version=source_report.version,
        artifact_path=artifact_path,
        sha256=artifact_report.sha256,
        size_bytes=artifact_report.size_bytes,
        files=artifact_report.files,
    )


def inspect_desktop_extension_artifact(
    *,
    artifact_path: Path,
    extension_root: Path,
) -> DesktopExtensionArtifactReport:
    """Reject unsafe, oversized, duplicated, or source-drifted bundle archives."""
    artifact_path = artifact_path.resolve()
    extension_root = extension_root.resolve()
    with zipfile.ZipFile(artifact_path) as archive:
        file_infos = [info for info in archive.infolist() if not info.is_dir()]
        file_names = [info.filename for info in file_infos]
        if len(file_names) != len(set(file_names)):
            msg = "MCPB archive contains duplicate paths"
            raise ValueError(msg)

        for info in file_infos:
            _validate_archive_path(info)
        uncompressed_size = sum(info.file_size for info in file_infos)
        if uncompressed_size > _MAX_UNCOMPRESSED_BYTES:
            msg = "MCPB archive exceeds the 5 MiB limit"
            raise ValueError(msg)

        files = set(file_names)
        forbidden = sorted(path for path in files if _is_forbidden_path(path))
        if forbidden:
            msg = f"MCPB archive contains forbidden file: {forbidden[0]}"
            raise ValueError(msg)
        missing = sorted(_REQUIRED_ARCHIVE_FILES - files)
        if missing:
            msg = f"MCPB archive is missing required files: {', '.join(missing)}"
            raise ValueError(msg)
        unexpected = sorted(files - _REQUIRED_ARCHIVE_FILES)
        if unexpected:
            msg = f"MCPB archive contains unexpected files: {', '.join(unexpected)}"
            raise ValueError(msg)

        corrupt_path = archive.testzip()
        if corrupt_path is not None:
            msg = f"MCPB archive contains corrupt file: {corrupt_path}"
            raise ValueError(msg)
        for relative_path in sorted(_REQUIRED_ARCHIVE_FILES):
            source_bytes = (extension_root / relative_path).read_bytes()
            if archive.read(relative_path) != source_bytes:
                msg = f"MCPB archive file {relative_path!r} does not match bundle source"
                raise ValueError(msg)

    return DesktopExtensionArtifactReport(
        sha256=hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
        size_bytes=artifact_path.stat().st_size,
        files=tuple(sorted(file_names)),
    )


def _validate_archive_path(info: zipfile.ZipInfo) -> None:
    """Require a normalized relative path and reject archived symlinks."""
    path = PurePosixPath(info.filename)
    if path.is_absolute() or ".." in path.parts or "\\" in info.filename:
        msg = f"MCPB archive contains unsafe path: {info.filename}"
        raise ValueError(msg)
    unix_mode = info.external_attr >> 16
    if unix_mode and stat.S_ISLNK(unix_mode):
        msg = f"MCPB archive contains unsafe symlink: {info.filename}"
        raise ValueError(msg)


def _is_forbidden_path(value: str) -> bool:
    path = PurePosixPath(value)
    return path.name in _FORBIDDEN_FILENAMES or path.name.startswith(".env.") or path.suffix in _FORBIDDEN_SUFFIXES


def _run_command(command: Sequence[str], *, cwd: Path) -> None:
    """Run a fixed-shape official MCPB CLI command without a shell."""
    subprocess.run(command, cwd=cwd, check=True, text=True)  # noqa: S603


def main() -> None:
    """CLI entrypoint for local and release MCPB builds."""
    parser = argparse.ArgumentParser(description="Build the Claude Desktop MCPB artifact.")
    parser.add_argument("--extension-root", type=Path, default=Path("desktop-extension"))
    parser.add_argument("--pyproject", type=Path, default=Path("pyproject.toml"))
    parser.add_argument("--output-dir", type=Path, default=Path("dist/mcpb"))
    args = parser.parse_args()
    try:
        report = build_desktop_extension(
            extension_root=args.extension_root,
            pyproject_path=args.pyproject,
            output_dir=args.output_dir,
        )
    except (OSError, subprocess.CalledProcessError, TypeError, ValueError, zipfile.BadZipFile) as exc:
        sys.stderr.write(f"Claude Desktop MCPB build failed: {exc}\n")
        raise SystemExit(1) from exc
    sys.stdout.write(f"Built {report.artifact_path} ({report.size_bytes} bytes, sha256 {report.sha256})\n")


if __name__ == "__main__":
    main()
