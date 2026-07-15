"""Check capability-profile surfaces and workflow fallback over MCP stdio."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextResourceContents
from pydantic import AnyUrl

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from albumentationsx_mcp.adapters.mcp.contracts import AdapterSurface, CombinedSurface
from albumentationsx_mcp.adapters.mcp.registration import surface_for_profile
from albumentationsx_mcp.capabilities import CapabilityProfile


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
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            resources_result = await session.list_resources()
            templates_result = await session.list_resource_templates()
            prompts_result = await session.list_prompts()
            diagnostics_result = await session.call_tool("diagnose_environment", {"include_write_probe": False})
            smoke_result = await session.call_tool("run_host_smoke_check", {"include_write_probe": False})
            resource_result = await session.read_resource(AnyUrl("albumentationsx://examples/client-smoke"))
            fallback_result = await session.call_tool(
                "get_workflow_example",
                {"example_id": "client-smoke"},
            )

        observed = AdapterSurface(
            adapter=f"stdio-{profile.value}",
            tools=tuple(tool.name for tool in tools_result.tools),
            resources=tuple(str(resource.uri) for resource in resources_result.resources),
            resource_templates=tuple(str(template.uriTemplate) for template in templates_result.resourceTemplates),
            prompts=tuple(prompt.name for prompt in prompts_result.prompts),
        )
        mismatches = _surface_mismatches(expected, observed)
        diagnostics = _structured_content(diagnostics_result.structuredContent, label="diagnose_environment")
        smoke = _structured_content(smoke_result.structuredContent, label="run_host_smoke_check")
        fallback = _structured_content(fallback_result.structuredContent, label="get_workflow_example")
        resource = _resource_json(resource_result.contents)
        expected_preview_ready = profile is not CapabilityProfile.CORE
        profile_identity_failures = _profile_identity_failures(
            diagnostics=diagnostics,
            smoke=smoke,
            expected=profile,
        )
        diagnostics_ok = diagnostics_result.isError is not True
        reported_capability_profile = smoke.get("capability_profile")
        preview_ready = smoke.get("preview_ready")
        smoke_ok = smoke_result.isError is not True and preview_ready is expected_preview_ready
        fallback_matches_resource = fallback_result.isError is not True and fallback == resource
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
        "schema_version": 2,
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
