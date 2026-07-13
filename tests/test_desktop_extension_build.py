from __future__ import annotations

import shutil
import warnings
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from scripts.build_desktop_extension import (
    MCPB_CLI_PACKAGE,
    build_desktop_extension,
    inspect_desktop_extension_artifact,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

ROOT = Path(__file__).resolve().parents[1]


def test_build_desktop_extension_uses_pinned_official_cli_and_stable_name(tmp_path: Path) -> None:
    extension_root, pyproject_path = _copy_bundle(tmp_path)
    output_dir = tmp_path / "dist"
    stale_artifact = output_dir / "albumentationsx-mcp-1.17.1.mcpb"
    output_dir.mkdir()
    stale_artifact.write_bytes(b"stale")
    commands: list[tuple[list[str], Path]] = []

    def run_command(command: Sequence[str], *, cwd: Path) -> None:
        normalized = list(command)
        commands.append((normalized, cwd))
        if "pack" in normalized:
            _pack_fixture(extension_root, Path(normalized[-1]))

    report = build_desktop_extension(
        extension_root=extension_root,
        pyproject_path=pyproject_path,
        output_dir=output_dir,
        command_runner=run_command,
    )

    assert report.artifact_path == stale_artifact.resolve()
    assert report.version == "1.17.1"
    assert report.sha256
    assert report.size_bytes > 0
    assert report.files == (
        "README.md",
        "icon.png",
        "manifest.json",
        "pyproject.toml",
        "src/server.py",
    )
    assert commands == [
        (
            [
                "npx",
                "--yes",
                "--package",
                MCPB_CLI_PACKAGE,
                "mcpb",
                "validate",
                str((extension_root / "manifest.json").resolve()),
            ],
            tmp_path.resolve(),
        ),
        (
            [
                "npx",
                "--yes",
                "--package",
                MCPB_CLI_PACKAGE,
                "mcpb",
                "pack",
                str(extension_root.resolve()),
                str(stale_artifact.resolve()),
            ],
            tmp_path.resolve(),
        ),
    ]
    assert stale_artifact.read_bytes() != b"stale"


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("missing_wrapper", "missing required files"),
        ("secret", "forbidden file"),
        ("manifest_drift", "does not match bundle source"),
        ("traversal", "unsafe path"),
        ("duplicate", "duplicate paths"),
    ],
)
def test_inspect_desktop_extension_artifact_rejects_unsafe_archive(
    tmp_path: Path,
    mutation: str,
    message: str,
) -> None:
    extension_root, _ = _copy_bundle(tmp_path)
    artifact_path = tmp_path / "unsafe.mcpb"
    _pack_fixture(extension_root, artifact_path, mutation=mutation)

    with pytest.raises(ValueError, match=message):
        inspect_desktop_extension_artifact(
            artifact_path=artifact_path,
            extension_root=extension_root,
        )


def test_inspect_desktop_extension_artifact_rejects_oversized_bundle(tmp_path: Path) -> None:
    extension_root, _ = _copy_bundle(tmp_path)
    artifact_path = tmp_path / "oversized.mcpb"
    _pack_fixture(extension_root, artifact_path, extra_bytes=5 * 1024 * 1024)

    with pytest.raises(ValueError, match="exceeds the 5 MiB limit"):
        inspect_desktop_extension_artifact(
            artifact_path=artifact_path,
            extension_root=extension_root,
        )


def _copy_bundle(tmp_path: Path) -> tuple[Path, Path]:
    extension_root = tmp_path / "desktop-extension"
    shutil.copytree(ROOT / "desktop-extension", extension_root)
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text('[project]\nversion = "1.17.1"\n', encoding="utf-8")
    return extension_root, pyproject_path


def _pack_fixture(
    extension_root: Path,
    artifact_path: Path,
    *,
    mutation: str | None = None,
    extra_bytes: int = 0,
) -> None:
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(artifact_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(extension_root.rglob("*")):
            if not path.is_file():
                continue
            relative_path = path.relative_to(extension_root).as_posix()
            if relative_path == ".mcpbignore":
                continue
            if mutation == "missing_wrapper" and relative_path == "src/server.py":
                continue
            data = path.read_bytes()
            if mutation == "manifest_drift" and relative_path == "manifest.json":
                data += b"\n"
            archive.writestr(relative_path, data)
        if mutation == "secret":
            archive.writestr(".env", "TOKEN=secret\n")
        elif mutation == "traversal":
            archive.writestr("../escape.txt", "escape\n")
        elif mutation == "duplicate":
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                archive.writestr("README.md", "duplicate\n")
        if extra_bytes:
            archive.writestr("large.bin", b"0" * extra_bytes)
