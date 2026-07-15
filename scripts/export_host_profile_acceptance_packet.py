"""Export a bounded capability-profile acceptance packet for real MCP hosts."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal, TypedDict

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from albumentationsx_mcp.capabilities import CapabilityProfile

HostName = Literal["Codex", "Claude Desktop"]
_SUPPORTED_HOSTS: tuple[HostName, ...] = ("Codex", "Claude Desktop")


class _ServerEntry(TypedDict):
    command: str
    args: list[str]


@dataclass(frozen=True)
class HostProfileAcceptancePacketConfig:
    """Inputs used to build one no-write real-host profile acceptance packet."""

    server_python: Path
    source_revision: str
    allowed_root: Path
    artifact_root: Path
    sample_image: Path
    run_date: str
    hosts: tuple[HostName, ...] = _SUPPORTED_HOSTS


def build_host_profile_acceptance_artifacts(config: HostProfileAcceptancePacketConfig) -> dict[str, str]:
    """Build deterministic operator files without mutating host configuration or evidence records."""
    _validate_config(config)
    server_entries: dict[str, _ServerEntry] = {
        _server_name(profile): {
            "command": str(config.server_python),
            "args": _server_args(config, profile),
        }
        for profile in CapabilityProfile
    }
    return {
        "README.md": _render_readme(config),
        "codex-config.toml": _render_codex_config(server_entries),
        "claude-desktop-config.json": json.dumps(
            {"mcpServers": server_entries},
            indent=2,
            sort_keys=False,
        )
        + "\n",
        "profile-matrix-prompt.md": _render_profile_matrix_prompt(config),
        "claude-review-loop-prompt.md": _render_claude_review_loop_prompt(config),
        "receipt-template.json": json.dumps(_receipt_template(config), indent=2, sort_keys=True) + "\n",
    }


def main() -> None:
    """Write one host profile acceptance packet to an explicit local directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server-python", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--allowed-root", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--sample-image", type=Path, required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--host", action="append", choices=_SUPPORTED_HOSTS)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    config = HostProfileAcceptancePacketConfig(
        server_python=args.server_python,
        source_revision=args.revision,
        allowed_root=args.allowed_root,
        artifact_root=args.artifact_root,
        sample_image=args.sample_image,
        run_date=args.date,
        hosts=tuple(args.host) if args.host else _SUPPORTED_HOSTS,
    )
    artifacts = build_host_profile_acceptance_artifacts(config)
    output_dir = args.output_dir
    if not output_dir.is_absolute():
        msg = "output_dir must be absolute"
        raise ValueError(msg)
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename, content in artifacts.items():
        (output_dir / filename).write_text(content, encoding="utf-8")
    sys.stdout.write(f"wrote host profile acceptance packet with {len(artifacts)} artifacts to {output_dir}\n")


def _validate_config(config: HostProfileAcceptancePacketConfig) -> None:
    _require_absolute(config.server_python, "server_python")
    if not config.server_python.is_file() or not os.access(config.server_python, os.X_OK):
        msg = "server_python must be an executable file"
        raise ValueError(msg)

    _require_absolute(config.allowed_root, "allowed_root")
    if not config.allowed_root.is_dir():
        msg = "allowed_root must be an existing directory"
        raise ValueError(msg)

    _require_absolute(config.artifact_root, "artifact_root")
    _require_absolute(config.sample_image, "sample_image")
    if not config.sample_image.is_file():
        msg = "sample_image must be an existing file"
        raise ValueError(msg)

    allowed_root = config.allowed_root.resolve()
    artifact_root = config.artifact_root.resolve()
    sample_image = config.sample_image.resolve()
    if not sample_image.is_relative_to(allowed_root):
        msg = "sample_image must be contained by allowed_root"
        raise ValueError(msg)
    if artifact_root.is_relative_to(allowed_root):
        msg = "artifact_root must not be inside allowed_root"
        raise ValueError(msg)

    if not config.source_revision.strip():
        msg = "source_revision must not be empty"
        raise ValueError(msg)
    try:
        parsed_date = date.fromisoformat(config.run_date)
    except ValueError as exc:
        msg = "run_date must be an ISO date"
        raise ValueError(msg) from exc
    if parsed_date.isoformat() != config.run_date:
        msg = "run_date must be an ISO date"
        raise ValueError(msg)

    unsupported = [host for host in config.hosts if host not in _SUPPORTED_HOSTS]
    if unsupported:
        msg = f"unsupported host: {unsupported[0]}"
        raise ValueError(msg)
    if not config.hosts:
        msg = "at least one host is required"
        raise ValueError(msg)
    if len(set(config.hosts)) != len(config.hosts):
        msg = "hosts must not contain duplicates"
        raise ValueError(msg)


def _require_absolute(path: Path, field: str) -> None:
    if not path.is_absolute():
        msg = f"{field} must be absolute"
        raise ValueError(msg)


def _server_name(profile: CapabilityProfile) -> str:
    return f"albumentationsx_{profile.value}"


def _server_args(config: HostProfileAcceptancePacketConfig, profile: CapabilityProfile) -> list[str]:
    return [
        "-m",
        "albumentationsx_mcp",
        "--allowed-root",
        str(config.allowed_root),
        "--artifact-root",
        str(config.artifact_root / profile.value),
        "--capability-profile",
        profile.value,
    ]


def _render_codex_config(server_entries: dict[str, _ServerEntry]) -> str:
    sections: list[str] = []
    for server_name, entry in server_entries.items():
        command = json.dumps(entry["command"])
        args = ", ".join(json.dumps(item) for item in entry["args"])
        sections.extend(
            [
                f"[mcp_servers.{server_name}]",
                f"command = {command}",
                f"args = [{args}]",
                "tool_timeout_sec = 300",
                "",
            ]
        )
    return "\n".join(sections)


def _render_readme(config: HostProfileAcceptancePacketConfig) -> str:
    hosts = ", ".join(config.hosts)
    return f"""# Host Profile Acceptance Packet

Packet status: `template_only`

Source revision: `{config.source_revision}`

Run date: `{config.run_date}`

Target hosts: `{hosts}`

This packet does not mutate host configuration or canonical evidence records. Merge only the relevant generated
configuration into a host after reviewing it, and remove the temporary entries after the run.

## Execution Order

1. Run `scripts/check_host_profile_conformance.py` against the same revision. This is machine proof only.
2. Load the four temporary profile servers in Codex and run `profile-matrix-prompt.md`.
3. Load the same four servers in Claude Desktop and run `profile-matrix-prompt.md`.
4. In Claude Desktop, run `claude-review-loop-prompt.md` and inspect both contact sheets before accepting.
5. Fill `receipt-template.json` only from observed host output, then sanitize it before committing a receipt.

## Evidence Policy

- Generated configuration and prompts are not host evidence.
- Protocol conformance is machine proof, not a real host UI observation.
- The bounded sample review proves host behavior but is not beta or adoption evidence.
- Keep private images, absolute user paths, account data, credentials, and raw host logs out of committed receipts.
- A failed or incomplete gate remains `blocked` or `pending`; never infer `passed` from another layer.
"""


def _render_profile_matrix_prompt(config: HostProfileAcceptancePacketConfig) -> str:
    server_lines = "\n".join(
        f"- `{_server_name(profile)}` must report capability profile `{profile.value}`."
        for profile in CapabilityProfile
    )
    return f"""# Capability Profile Matrix Prompt

Use only these temporary AlbumentationsX MCP servers from source revision `{config.source_revision}`:

{server_lines}

For each server, in the listed order:

1. Confirm that the server's tools are discoverable.
2. If this host exposes MCP resource reads to the model, read `albumentationsx://examples/client-smoke`.
3. If resource reads are unavailable, call `get_workflow_example` with `example_id="client-smoke"` instead.
4. Call `run_host_smoke_check` with `include_write_probe=false`.
5. Record the reported capability profile, whether preview is ready, the resource path used (`resource` or `fallback`),
   and the first failing gate if any.

Do not render images and do not modify host configuration during this matrix check. Return one concise JSON object with
`source_revision`, `host`, and one result per profile. Do not include absolute filesystem paths or raw tool output.
"""


def _render_claude_review_loop_prompt(config: HostProfileAcceptancePacketConfig) -> str:
    review_gate = (
        "Do not accept the candidate until the reviewer has inspected it and explicitly confirmed that it remains "
        "recognizable."
    )
    return f"""# Claude Desktop Review Loop Prompt

Use only the `albumentationsx_review` MCP server from source revision `{config.source_revision}` and this generated
sample image:

`{config.sample_image}`

1. Call `run_host_smoke_check` with `include_write_probe=true`; stop if `preview_ready` is not true.
2. Build this baseline request, call `validate_preview_request`, then call `render_preview_batch` only if valid:

```json
{{
  "input_paths": ["{config.sample_image}"],
  "pipeline": {{
    "transforms": [
      {{"name": "GaussNoise", "params": {{"std_range": [0.1, 0.4]}}, "p": 0.8}}
    ]
  }},
  "variants_per_image": 2,
  "seed": 17
}}
```

3. Show the baseline contact sheet to the reviewer. Do not make the review decision yourself.
4. After the reviewer rejects it, call `record_preview_feedback` for image `0`, variant `0`, with
   `feedback_tags=["too_noisy:high"]`, `accepted=false`, and a short note.
5. Call `adjust_pipeline` with the baseline pipeline and `feedback_tags=["too_noisy:high"]`.
6. Reuse the request with the returned pipeline and seed `18`, validate it, and call `render_preview_batch`.
7. Call `compare_preview_runs` with the baseline and candidate run IDs and `quality_profile="classification"`.
8. Show the candidate contact sheet and comparison to the reviewer. {review_gate}
9. Only after confirmation, call `record_preview_feedback` on candidate image `0`, variant `0`, with
   `feedback_tags=["accepted"]` and `accepted=true`.
10. Return a privacy-safe summary containing run IDs, relative artifact names, fallback path, rejection tag, adjustment
    summary, comparison result, and reviewer decision. Do not include account data or absolute user paths.

This generated-fixture run is host workflow evidence only, not beta or adoption evidence.
"""


def _receipt_template(config: HostProfileAcceptancePacketConfig) -> dict[str, object]:
    hosts: list[dict[str, object]] = [
        {
            "fallback_status": "pending",
            "host": host,
            "profiles": [
                {
                    "preview_ready": "pending",
                    "profile": profile.value,
                    "resource_path": "pending",
                    "smoke_status": "pending",
                    "status": "pending",
                }
                for profile in CapabilityProfile
            ],
            "review_loop_status": "pending" if host == "Claude Desktop" else "not_requested",
            "status": "pending",
        }
        for host in config.hosts
    ]
    return {
        "artifacts": [],
        "evidence_classification": {
            "adoption_evidence": False,
            "host_evidence": "not_observed",
            "machine_proof": "not_run",
            "packet": "template_only",
        },
        "hosts": hosts,
        "run_date": config.run_date,
        "schema_version": 1,
        "source_revision": config.source_revision,
    }


if __name__ == "__main__":
    main()
