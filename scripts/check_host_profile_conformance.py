"""Check capability-profile surfaces and workflow fallback over MCP stdio."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextResourceContents

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from albumentationsx_mcp.adapters.mcp.contracts import AdapterSurface, CombinedSurface
from albumentationsx_mcp.adapters.mcp.registration import surface_for_profile
from albumentationsx_mcp.capabilities import CapabilityProfile

_FULL_COMMIT_ID = re.compile(r"[0-9a-f]{40}")
_SHA256_DIGEST = re.compile(r"[0-9a-f]{64}")
_GIT_TREE_ENTRY = re.compile(rb"(?P<mode>[0-7]{6}) (?P<kind>blob) (?P<object>[0-9a-f]{40}|[0-9a-f]{64})\t(?P<path>.+)")
_GIT_TIMEOUT_SECONDS = 5
_LEGACY_PROFILE_CONFORMANCE_SCHEMA_VERSION = 2
_PROFILE_CONFORMANCE_SCHEMA_VERSION = 3
_PROFILE_CONFORMANCE_RELEVANT_PATHS = (
    "src/albumentationsx_mcp",
    "scripts/check_host_profile_conformance.py",
    "pyproject.toml",
    "uv.lock",
)
_GIT_PROVENANCE_FAILURE = "Git provenance validation failed"


@dataclass(frozen=True)
class ProfileConformanceConfig:
    """Inputs for one privacy-safe current-source stdio conformance report."""

    server_python: Path
    source_root: Path
    source_revision: str
    allowed_root: Path
    artifact_root: Path


async def check_profile_conformance(
    config: ProfileConformanceConfig,
    profile: CapabilityProfile,
) -> dict[str, Any]:
    """Probe one profile over stdio and compare it to its canonical adapter surface."""
    _validate_config(config)
    expected = surface_for_profile(profile)
    params = StdioServerParameters(
        command=str(config.server_python),
        args=[
            "-m",
            "albumentationsx_mcp",
            "--allowed-root",
            str(config.allowed_root),
            "--artifact-root",
            str(config.artifact_root / profile.value),
            "--capability-profile",
            profile.value,
        ],
        cwd=str(config.source_root),
    )
    try:
        async with Client(stdio_client(params), mode="auto") as client:
            tools_result = await client.list_tools()
            resources_result = await client.list_resources()
            templates_result = await client.list_resource_templates()
            prompts_result = await client.list_prompts()
            diagnostics_result = await client.call_tool("diagnose_environment", {"include_write_probe": False})
            smoke_result = await client.call_tool("run_host_smoke_check", {"include_write_probe": False})
            resource_result = await client.read_resource("albumentationsx://examples/client-smoke")
            fallback_result = await client.call_tool(
                "get_workflow_example",
                {"example_id": "client-smoke"},
            )

        raw_observed = AdapterSurface(
            adapter=f"stdio-{profile.value}",
            tools=tuple(tool.name for tool in tools_result.tools),
            resources=tuple(str(resource.uri) for resource in resources_result.resources),
            resource_templates=tuple(str(template.uri_template) for template in templates_result.resource_templates),
            prompts=tuple(prompt.name for prompt in prompts_result.prompts),
        )
        observed = _canonicalize_surface(expected, raw_observed)
        mismatches = _surface_mismatches(expected, observed)
        diagnostics = _structured_content(diagnostics_result.structured_content, label="diagnose_environment")
        smoke = _structured_content(smoke_result.structured_content, label="run_host_smoke_check")
        fallback = _structured_content(fallback_result.structured_content, label="get_workflow_example")
        resource = _resource_json(resource_result.contents)
        expected_preview_ready = profile is not CapabilityProfile.CORE
        profile_identity_failures = _profile_identity_failures(
            diagnostics=diagnostics,
            smoke=smoke,
            expected=profile,
        )
        diagnostics_ok = diagnostics_result.is_error is not True
        reported_capability_profile = smoke.get("capability_profile")
        preview_ready = smoke.get("preview_ready")
        smoke_ok = smoke_result.is_error is not True and preview_ready is expected_preview_ready
        fallback_matches_resource = fallback_result.is_error is not True and fallback == resource
        failures = _profile_failures(
            mismatches=mismatches,
            diagnostics_ok=diagnostics_ok,
            smoke_ok=smoke_ok,
            profile_identity_failures=profile_identity_failures,
            fallback_matches_resource=fallback_matches_resource,
        )
        return {
            "diagnostics_ok": diagnostics_ok,
            "diagnostics_reported_capability_profile": diagnostics.get("capability_profile"),
            "failures": failures,
            "fallback_matches_resource": fallback_matches_resource,
            "preview_ready": preview_ready,
            "profile": profile.value,
            "profile_identity_matches": not profile_identity_failures,
            "reported_capability_profile": reported_capability_profile,
            "smoke_ok": smoke_ok,
            "status": "passed" if not failures else "failed",
            "surface": _surface_summary(observed),
            "surface_matches": not mismatches,
            "surface_mismatches": mismatches,
        }
    except Exception as exc:  # noqa: BLE001 - profile boundary must report a failed probe, not abort the matrix.
        return {
            "diagnostics_ok": False,
            "diagnostics_reported_capability_profile": None,
            "failures": [_sanitized_failure(config, exc)],
            "fallback_matches_resource": False,
            "preview_ready": None,
            "profile": profile.value,
            "profile_identity_matches": False,
            "reported_capability_profile": None,
            "smoke_ok": False,
            "status": "failed",
            "surface": _empty_surface_summary(),
            "surface_matches": False,
            "surface_mismatches": {"probe": "profile probe did not complete"},
        }


async def build_profile_conformance_report(config: ProfileConformanceConfig) -> dict[str, Any]:
    """Run the deterministic conformance matrix in canonical profile order."""
    _validate_config(config)
    profiles = await asyncio.gather(*(check_profile_conformance(config, profile) for profile in CapabilityProfile))
    return {
        "evidence_classification": "machine_proof_only",
        "profiles": list(profiles),
        "relevant_tree_sha256": relevant_tree_sha256(config.source_root, config.source_revision),
        "schema_version": _PROFILE_CONFORMANCE_SCHEMA_VERSION,
        "source_revision": config.source_revision,
        "status": "passed" if all(item["status"] == "passed" for item in profiles) else "failed",
        "transport": "stdio",
    }


def render_profile_conformance_report(report: dict[str, Any]) -> str:
    """Render one deterministic conformance report as JSON."""
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def profile_conformance_exit_code(report: dict[str, Any]) -> int:
    """Map report status to a shell exit code."""
    return 0 if report.get("status") == "passed" else 1


def source_head_revision(source_root: Path) -> str:
    """Return the full commit id for source_root HEAD."""
    head = _resolve_git_commit(source_root, "HEAD")
    if head is None:
        msg = "source_root Git HEAD is unavailable"
        raise ValueError(msg)
    return head


def validate_generation_revision(*, source_root: Path, source_revision: str) -> str:
    """Require publication to label the exact source-root HEAD it executes."""
    revision = _validated_source_revision(source_revision)
    resolved_revision = _resolve_git_commit(source_root, revision)
    if resolved_revision is None:
        msg = "source_revision does not identify a commit in source_root"
        raise ValueError(msg)
    head = source_head_revision(source_root)
    if resolved_revision != head:
        msg = "source_revision must equal source_root Git HEAD"
        raise ValueError(msg)
    return head


def validate_committed_report_provenance(
    report: Mapping[str, Any],
    *,
    source_root: Path,
) -> str:
    """Validate that committed evidence still describes current relevant sources."""
    revision = _validated_source_revision(report.get("source_revision"))
    schema_version = report.get("schema_version", _LEGACY_PROFILE_CONFORMANCE_SCHEMA_VERSION)
    if schema_version == _PROFILE_CONFORMANCE_SCHEMA_VERSION:
        return _validate_tree_bound_provenance(
            source_root=source_root,
            revision=revision,
            expected_digest=_validated_relevant_tree_digest(report.get("relevant_tree_sha256")),
        )
    if schema_version != _LEGACY_PROFILE_CONFORMANCE_SCHEMA_VERSION:
        msg = "unsupported profile conformance schema_version"
        raise ValueError(msg)

    resolved_revision = _resolve_git_commit(source_root, revision)
    if resolved_revision is None:
        msg = "source_revision does not identify a commit in source_root"
        raise ValueError(msg)
    head = source_head_revision(source_root)

    ancestor_status = _git_status(source_root, "merge-base", "--is-ancestor", resolved_revision, head)
    if ancestor_status == 1:
        msg = "evidence source_revision is not an ancestor of source_root Git HEAD"
        raise ValueError(msg)
    if ancestor_status != 0:
        raise ValueError(_GIT_PROVENANCE_FAILURE)

    drift_status = _git_status(
        source_root,
        "diff",
        "--quiet",
        f"{resolved_revision}..{head}",
        "--",
        *_PROFILE_CONFORMANCE_RELEVANT_PATHS,
    )
    if drift_status == 1:
        msg = "profile-conformance-relevant sources changed after evidence revision"
        raise ValueError(msg)
    if drift_status != 0:
        raise ValueError(_GIT_PROVENANCE_FAILURE)
    return resolved_revision


def relevant_tree_sha256(source_root: Path, revision: str) -> str:
    """Hash canonical Git entries that can affect the profile-conformance report."""
    resolved_revision = _resolve_git_commit(source_root, revision)
    if resolved_revision is None:
        msg = "source_revision does not identify a commit in source_root"
        raise ValueError(msg)
    listing = _git_output(
        source_root,
        "ls-tree",
        "-r",
        "-z",
        "--full-tree",
        resolved_revision,
        "--",
        *_PROFILE_CONFORMANCE_RELEVANT_PATHS,
    )
    _validate_relevant_tree_listing(listing)
    return hashlib.sha256(listing).hexdigest()


def _validate_tree_bound_provenance(
    *,
    source_root: Path,
    revision: str,
    expected_digest: str,
) -> str:
    head = source_head_revision(source_root)
    if relevant_tree_sha256(source_root, head) != expected_digest:
        msg = "profile-conformance-relevant sources changed after evidence revision"
        raise ValueError(msg)

    resolved_revision = _resolve_git_commit(source_root, revision)
    if resolved_revision is not None and relevant_tree_sha256(source_root, resolved_revision) != expected_digest:
        msg = "evidence source_revision does not match relevant_tree_sha256"
        raise ValueError(msg)
    return revision


def _validate_relevant_tree_listing(listing: bytes) -> None:
    if not listing or not listing.endswith(b"\0"):
        raise ValueError(_GIT_PROVENANCE_FAILURE)
    seen_paths: set[bytes] = set()
    allowed_paths = tuple(path.encode() for path in _PROFILE_CONFORMANCE_RELEVANT_PATHS)
    for raw_entry in listing[:-1].split(b"\0"):
        match = _GIT_TREE_ENTRY.fullmatch(raw_entry)
        if match is None:
            raise ValueError(_GIT_PROVENANCE_FAILURE)
        path = match.group("path")
        if path in seen_paths or not any(path == root or path.startswith(root + b"/") for root in allowed_paths):
            raise ValueError(_GIT_PROVENANCE_FAILURE)
        seen_paths.add(path)


def main() -> None:
    """Run the profile matrix and write a privacy-safe JSON report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server-python", type=Path, default=Path(sys.executable).absolute())
    parser.add_argument("--source-root", type=Path, default=Path.cwd().resolve())
    parser.add_argument("--revision", required=True)
    parser.add_argument("--allowed-root", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    config = ProfileConformanceConfig(
        server_python=args.server_python,
        source_root=args.source_root,
        source_revision=args.revision,
        allowed_root=args.allowed_root,
        artifact_root=args.artifact_root,
    )
    _validate_config(config)
    try:
        validate_generation_revision(
            source_root=config.source_root,
            source_revision=config.source_revision,
        )
    except ValueError as exc:
        sys.stderr.write(f"host profile conformance error: {exc}\n")
        raise SystemExit(2) from None
    report = asyncio.run(build_profile_conformance_report(config))
    if not args.output.is_absolute():
        msg = "output must be absolute"
        raise ValueError(msg)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_profile_conformance_report(report), encoding="utf-8")
    status = report["status"]
    sys.stdout.write(f"host profile conformance {status}; wrote report to {args.output}\n")
    raise SystemExit(profile_conformance_exit_code(report))


def _validate_config(config: ProfileConformanceConfig) -> None:
    _require_absolute(config.server_python, "server_python")
    if not config.server_python.is_file() or not os.access(config.server_python, os.X_OK):
        msg = "server_python must be an executable file"
        raise ValueError(msg)
    _require_absolute(config.source_root, "source_root")
    if not config.source_root.is_dir():
        msg = "source_root must be an existing directory"
        raise ValueError(msg)
    _require_absolute(config.allowed_root, "allowed_root")
    if not config.allowed_root.is_dir():
        msg = "allowed_root must be an existing directory"
        raise ValueError(msg)
    _require_absolute(config.artifact_root, "artifact_root")
    if config.artifact_root.resolve().is_relative_to(config.allowed_root.resolve()):
        msg = "artifact_root must not be inside allowed_root"
        raise ValueError(msg)
    if not config.source_revision.strip():
        msg = "source_revision must not be empty"
        raise ValueError(msg)


def _require_absolute(path: Path, field: str) -> None:
    if not path.is_absolute():
        msg = f"{field} must be absolute"
        raise ValueError(msg)


def _validated_source_revision(value: Any) -> str:
    if not isinstance(value, str) or _FULL_COMMIT_ID.fullmatch(value) is None:
        msg = "source_revision must be a full Git commit id"
        raise ValueError(msg)
    return value


def _validated_relevant_tree_digest(value: Any) -> str:
    if not isinstance(value, str) or _SHA256_DIGEST.fullmatch(value) is None:
        msg = "relevant_tree_sha256 must be a SHA-256 digest"
        raise ValueError(msg)
    return value


def _resolve_git_commit(source_root: Path, revision: str) -> str | None:
    try:
        result = subprocess.run(  # noqa: S603 - fixed Git executable with argument-list inputs only.
            [  # noqa: S607 - Git is resolved from the controlled publication environment.
                "git",
                "-C",
                str(source_root),
                "rev-parse",
                "--verify",
                "--quiet",
                f"{revision}^{{commit}}",
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=_GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise ValueError(_GIT_PROVENANCE_FAILURE) from None
    if result.returncode != 0:
        return None
    commit_id = result.stdout.strip()
    if _FULL_COMMIT_ID.fullmatch(commit_id) is None:
        raise ValueError(_GIT_PROVENANCE_FAILURE)
    return commit_id


def _git_status(source_root: Path, *args: str) -> int:
    try:
        result = subprocess.run(  # noqa: S603 - fixed Git executable with argument-list inputs only.
            ["git", "-C", str(source_root), *args],  # noqa: S607 - controlled publication environment.
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=_GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise ValueError(_GIT_PROVENANCE_FAILURE) from None
    return result.returncode


def _git_output(source_root: Path, *args: str) -> bytes:
    try:
        result = subprocess.run(  # noqa: S603 - fixed Git executable with argument-list inputs only.
            ["git", "-C", str(source_root), *args],  # noqa: S607 - controlled publication environment.
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=_GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise ValueError(_GIT_PROVENANCE_FAILURE) from None
    if result.returncode != 0:
        raise ValueError(_GIT_PROVENANCE_FAILURE)
    return result.stdout


def _surface_mismatches(
    expected: AdapterSurface | CombinedSurface,
    observed: AdapterSurface | CombinedSurface,
) -> dict[str, dict[str, list[str]]]:
    mismatches: dict[str, dict[str, list[str]]] = {}
    for field in ("tools", "resources", "resource_templates", "prompts"):
        expected_values = list(getattr(expected, field))
        observed_values = list(getattr(observed, field))
        if observed_values != expected_values:
            mismatches[field] = {
                "expected": expected_values,
                "observed": observed_values,
            }
    return mismatches


def _canonicalize_surface(expected: CombinedSurface, observed: AdapterSurface) -> AdapterSurface:
    return AdapterSurface(
        adapter=observed.adapter,
        tools=_canonicalize_identifiers(expected.tools, observed.tools),
        resources=_canonicalize_identifiers(expected.resources, observed.resources),
        resource_templates=_canonicalize_identifiers(expected.resource_templates, observed.resource_templates),
        prompts=_canonicalize_identifiers(expected.prompts, observed.prompts),
    )


def _canonicalize_identifiers(expected: Sequence[str], observed: Sequence[str]) -> tuple[str, ...]:
    observed_set = set(observed)
    canonical = [identifier for identifier in expected if identifier in observed_set]
    canonical.extend(sorted(identifier for identifier in observed if identifier not in set(expected)))
    return tuple(canonical)


def _surface_summary(surface: AdapterSurface) -> dict[str, int | str]:
    return {
        "prompt_count": len(surface.prompts),
        "prompts_sha256": _sequence_digest(surface.prompts),
        "resource_count": len(surface.resources),
        "resource_template_count": len(surface.resource_templates),
        "resource_templates_sha256": _sequence_digest(surface.resource_templates),
        "resources_sha256": _sequence_digest(surface.resources),
        "tool_count": len(surface.tools),
        "tools_sha256": _sequence_digest(surface.tools),
    }


def _empty_surface_summary() -> dict[str, int | str]:
    return _surface_summary(AdapterSurface(adapter="failed-probe"))


def _sequence_digest(values: Sequence[str]) -> str:
    encoded = json.dumps(list(values), ensure_ascii=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _structured_content(value: dict[str, Any] | None, *, label: str) -> dict[str, Any]:
    if value is None:
        msg = f"{label} returned no structured content"
        raise ValueError(msg)
    return value


def _resource_json(contents: list[Any]) -> dict[str, Any]:
    if len(contents) != 1 or not isinstance(contents[0], TextResourceContents):
        msg = "client-smoke resource returned an unsupported content shape"
        raise ValueError(msg)
    payload = json.loads(contents[0].text)
    if not isinstance(payload, dict):
        msg = "client-smoke resource must contain a JSON object"
        raise TypeError(msg)
    return payload


def _profile_failures(
    *,
    mismatches: dict[str, Any],
    diagnostics_ok: bool,
    smoke_ok: bool,
    profile_identity_failures: list[str],
    fallback_matches_resource: bool,
) -> list[str]:
    failures: list[str] = []
    if mismatches:
        failures.append("observed MCP surface differs from the canonical profile")
    if not diagnostics_ok:
        failures.append("diagnose_environment returned an MCP tool error")
    failures.extend(profile_identity_failures)
    if not smoke_ok:
        failures.append("host smoke result does not match profile preview semantics")
    if not fallback_matches_resource:
        failures.append("client-smoke fallback differs from the canonical resource")
    return failures


def _profile_identity_failures(
    *,
    diagnostics: dict[str, Any],
    smoke: dict[str, Any],
    expected: CapabilityProfile,
) -> list[str]:
    failures: list[str] = []
    for tool, payload in (
        ("diagnose_environment", diagnostics),
        ("run_host_smoke_check", smoke),
    ):
        if payload.get("capability_profile") != expected.value:
            failures.append(f"{tool} did not report capability profile {expected.value!r}")
    return failures


def _sanitized_failure(config: ProfileConformanceConfig, exc: Exception) -> str:
    message = str(exc)
    replacements = {
        str(config.server_python): "<server-python>",
        str(config.source_root): "<source-root>",
        str(config.allowed_root): "<allowed-root>",
        str(config.artifact_root): "<artifact-root>",
    }
    for private_value, replacement in replacements.items():
        message = message.replace(private_value, replacement)
    return f"{type(exc).__name__}: {message}"


if __name__ == "__main__":
    main()
