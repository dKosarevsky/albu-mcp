import subprocess
import sys
from pathlib import Path

from scripts.export_manual_host_acceptance_packet import (
    ManualHostAcceptancePacketConfig,
    build_manual_host_acceptance_packet,
)


def test_manual_host_acceptance_packet_contains_host_configs_and_record_commands(tmp_path: Path) -> None:
    allowed_root = tmp_path / "inputs"
    artifact_root = tmp_path / "artifacts"
    sample_image = allowed_root / "sample-grid.png"
    config = ManualHostAcceptancePacketConfig(
        allowed_root=allowed_root,
        artifact_root=artifact_root,
        sample_image=sample_image,
        package_version="1.13.0",
        run_date="2026-06-20",
    )

    packet = build_manual_host_acceptance_packet(config)

    assert "uvx" in packet
    assert "albumentationsx-mcp==1.13.0" in packet
    assert str(allowed_root) in packet
    assert str(artifact_root) in packet
    assert str(sample_image) in packet
    assert "Claude Desktop" in packet
    assert "Claude Code" in packet
    assert "Cursor" in packet
    assert "Codex" in packet
    assert "albumentationsx://examples/distortion-review" in packet
    assert "run_host_smoke_check" in packet
    assert "compare_preview_runs" in packet
    assert "export_tuning_session" in packet
    assert "record_host_manual_run.py --host 'Claude Desktop' --status passed --date 2026-06-20" in packet
    assert "record_host_manual_run.py --host Codex --status passed --date 2026-06-20" in packet
    assert '"status": "passed"' not in packet


def test_manual_host_acceptance_packet_can_target_one_host(tmp_path: Path) -> None:
    config = ManualHostAcceptancePacketConfig(
        allowed_root=tmp_path / "inputs",
        artifact_root=tmp_path / "artifacts",
        sample_image=tmp_path / "inputs" / "sample-grid.png",
        package_version="1.13.0",
        run_date="2026-06-20",
        hosts=("Cursor",),
    )

    packet = build_manual_host_acceptance_packet(config)

    assert "## Cursor" in packet
    assert "## Claude Desktop" not in packet
    assert "## Claude Code" not in packet
    assert "## Codex" not in packet
    assert "### Cursor Evidence Checklist" in packet
    assert "record_host_manual_run.py --host Cursor --status passed --date 2026-06-20" in packet
    assert "record_host_manual_run.py --host Cursor --status blocked --date 2026-06-20" in packet
    assert "record_host_manual_run.py --host Cursor --status pending --date 2026-06-20" in packet


def test_manual_host_acceptance_packet_cli_writes_markdown(tmp_path: Path) -> None:
    allowed_root = tmp_path / "inputs"
    artifact_root = tmp_path / "artifacts"
    allowed_root.mkdir()
    sample_image = allowed_root / "sample-grid.png"
    sample_image.write_bytes(b"not-a-real-image-for-packet-generation")
    output_path = tmp_path / "packet.md"

    result = subprocess.run(  # noqa: S603 - static script path with controlled fixture paths.
        [
            sys.executable,
            "scripts/export_manual_host_acceptance_packet.py",
            "--allowed-root",
            str(allowed_root),
            "--artifact-root",
            str(artifact_root),
            "--sample-image",
            str(sample_image),
            "--date",
            "2026-06-20",
            "--package-version",
            "1.13.0",
            "--host",
            "Cursor",
            "--output",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert f"wrote manual host acceptance packet: {output_path}" in result.stdout
    packet = output_path.read_text(encoding="utf-8")
    assert "# Manual Host Acceptance Packet" in packet
    assert str(sample_image.resolve()) in packet
    assert "## Cursor" in packet
    assert "## Codex" not in packet
