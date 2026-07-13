import json
from pathlib import Path

import tomli
import yaml


def test_readme_first_sentence_links_to_albumentationsx_repo() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert readme.startswith(
        "# AlbumentationsX MCP\n\n"
        "Model Context Protocol server for "
        "[AlbumentationsX](https://github.com/albumentations-team/AlbumentationsX)",
    )


def test_ci_workflow_runs_core_quality_gates() -> None:
    workflow_path = Path(".github/workflows/ci.yml")
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["test"]["steps"]
    commands = "\n".join(step.get("run", "") for step in steps)

    assert workflow["jobs"]["test"]["strategy"]["matrix"]["python-version"] == ["3.10", "3.11", "3.12", "3.13"]
    assert "uv run pytest" in commands
    assert "uv run ruff check ." in commands
    assert "uv run ruff format --check ." in commands
    assert "uv run ty check" in commands
    assert "uv build" in commands
    assert "uv run python scripts/run_golden_evals.py" in commands
    assert "uv run python scripts/validate_host_manual_runs.py" in commands
    assert "uv run python scripts/check_host_acceptance_report.py" in commands
    assert "uv run python scripts/check_contract_snapshots.py" in commands
    assert "uv run python scripts/check_demo_assets.py --output-dir docs/assets/demo --check" in commands
    assert "uv run python scripts/check_release_readiness.py" in commands
    assert "ClientSession" in commands


def test_ci_workflow_builds_and_verifies_the_mcp_app() -> None:
    workflow = yaml.safe_load(Path(".github/workflows/ci.yml").read_text(encoding="utf-8"))
    ui_job = workflow["jobs"]["ui"]
    steps = ui_job["steps"]
    commands = "\n".join(step.get("run", "") for step in steps)
    setup_node = next(step for step in steps if step.get("name") == "Set up Node.js")

    assert setup_node["uses"] == "actions/setup-node@v6"
    assert setup_node["with"] == {
        "node-version": "24",
        "cache": "npm",
        "cache-dependency-path": "mcp-app/package-lock.json",
    }
    for command in [
        "npm --prefix mcp-app ci",
        "npm --prefix mcp-app run test",
        "npm --prefix mcp-app run typecheck",
        "npm --prefix mcp-app run format:check",
        "npm --prefix mcp-app run build",
        "git diff --exit-code -- src/albumentationsx_mcp/ui/preview-review.html",
    ]:
        assert command in commands


def test_release_workflow_builds_ui_before_python_distributions() -> None:
    workflow = yaml.safe_load(Path(".github/workflows/release.yml").read_text(encoding="utf-8"))
    steps = workflow["jobs"]["build"]["steps"]
    commands = "\n".join(step.get("run", "") for step in steps)

    ui_build = commands.index("npm --prefix mcp-app run build")
    python_build = commands.index("uv build")
    bundle_check = commands.index("scripts/check_mcp_app_bundle.py --dist-dir dist")
    assert ui_build < python_build < bundle_check


def test_mcp_registry_watchdog_workflow_checks_latest_registry_entry() -> None:
    workflow_path = Path(".github/workflows/mcp-registry-watchdog.yml")
    workflow_text = workflow_path.read_text(encoding="utf-8")
    workflow = yaml.safe_load(workflow_text)
    steps = workflow["jobs"]["check"]["steps"]
    commands = "\n".join(step.get("run", "") for step in steps)

    assert "workflow_dispatch:" in workflow_text
    assert "schedule:" in workflow_text
    assert "python scripts/check_mcp_registry_status.py" in commands
    assert "actions/checkout@v5" in workflow_text
    assert "actions/setup-python@v6" in workflow_text


def test_ci_workflow_uses_node24_ready_actions() -> None:
    workflow_path = Path(".github/workflows/ci.yml")
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["test"]["steps"]
    actions = {step["name"]: step["uses"] for step in steps if "uses" in step}
    setup_uv = next(step for step in steps if step.get("name") == "Install uv")

    assert actions["Check out repository"] == "actions/checkout@v5"
    assert actions["Install uv"] == "astral-sh/setup-uv@v7"
    assert actions["Set up Python"] == "actions/setup-python@v6"
    assert setup_uv["with"]["enable-cache"] is False


def test_runtime_dependency_keeps_mcp_sdk_on_v1() -> None:
    project = tomli.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]
    mcp_requirements = [requirement for requirement in project["dependencies"] if requirement.startswith("mcp[")]

    assert mcp_requirements == ["mcp[cli]>=1.24.0,<2"]


def test_usage_docs_and_examples_are_present() -> None:
    assert Path("docs/USAGE.md").exists()
    assert Path("docs/INSTALL.md").exists()
    assert Path("docs/ADOPTION.md").exists()
    assert Path("docs/HOST_ACCEPTANCE.md").exists()
    assert Path("docs/HOST_MATRIX.md").exists()
    assert Path("docs/RELEASE.md").exists()
    assert Path("docs/RECIPES.md").exists()
    assert Path("CHANGELOG.md").exists()
    assert Path("server.json").exists()
    assert Path("examples/claude_desktop_config.json").exists()
    assert Path("examples/claude_desktop_pypi_config.json").exists()
    assert Path("examples/claude_desktop_preview_config.json").exists()
    assert Path("examples/claude_code_preview_command.md").exists()
    assert Path("examples/cursor_mcp_config.json").exists()
    assert Path("examples/cursor_preview_mcp_config.json").exists()
    assert Path("examples/codex_mcp_config.toml").exists()
    assert Path("examples/codex_preview_mcp_config.toml").exists()
    assert Path("examples/first_preview_workflow.md").exists()
    assert Path("examples/classification_pipeline.json").exists()
    assert Path("scripts/render_demo_assets.py").exists()
    assert Path("scripts/check_demo_assets.py").exists()
    assert Path("docs/DEMO.md").exists()
    assert Path("docs/assets/demo/demo_manifest.json").exists()
    assert Path("docs/assets/demo/demo_report.md").exists()


def test_mcp_apps_review_guide_documents_progressive_enhancement() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    install = Path("docs/INSTALL.md").read_text(encoding="utf-8")
    usage = Path("docs/USAGE.md").read_text(encoding="utf-8")
    guide = Path("docs/MCP_APPS_REVIEW.md").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8").split("## 1.17.1", 1)[0]

    for content in [readme, install, usage]:
        assert "[docs/MCP_APPS_REVIEW.md](docs/MCP_APPS_REVIEW.md)" in content or (
            "[MCP_APPS_REVIEW.md](MCP_APPS_REVIEW.md)" in content
        )
    for term in [
        "ui://albumentationsx/preview-review.html",
        "artifact://{run_id}/{filename}",
        "record_preview_feedback",
        "progressive enhancement",
        "no outgoing network dependency",
        "manifest-recorded PNG",
        "non-MCP-Apps host",
        "not beta or adoption evidence",
    ]:
        assert term in guide
    assert "MCP Apps" in changelog


def test_adoption_packet_is_linked_and_actionable() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    adoption = Path("docs/ADOPTION.md").read_text(encoding="utf-8")

    assert "[docs/ADOPTION.md](docs/ADOPTION.md)" in readme
    for term in [
        "2-minute trial",
        "uvx --from albumentationsx-mcp albumentationsx-mcp",
        "Claude Desktop",
        "Cursor",
        "plan_dataset_onboarding",
        "segmentation",
        "compressed COCO RLE",
        "compare_preview_runs",
        "export_pipeline",
    ]:
        assert term in adoption


def test_v1_readiness_tracks_current_product_gate() -> None:
    readiness = Path("docs/V1_READINESS.md").read_text(encoding="utf-8")

    for term in [
        "v1.17.1",
        "albumentationsx-mcp==1.17.1",
        "MCP Registry",
        "build_review_packet",
        "review_packet_flow",
        "docs/HOST_PROOF_STATUS.md",
        "Manual Host UI",
        "Claude Code remains blocked",
    ]:
        assert term in readiness


def test_install_guide_covers_host_setup_and_examples() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    usage = Path("docs/USAGE.md").read_text(encoding="utf-8")
    install = Path("docs/INSTALL.md").read_text(encoding="utf-8")
    claude_pypi = json.loads(Path("examples/claude_desktop_pypi_config.json").read_text(encoding="utf-8"))
    claude_preview = json.loads(Path("examples/claude_desktop_preview_config.json").read_text(encoding="utf-8"))
    cursor = json.loads(Path("examples/cursor_mcp_config.json").read_text(encoding="utf-8"))
    cursor_preview = json.loads(Path("examples/cursor_preview_mcp_config.json").read_text(encoding="utf-8"))
    codex = Path("examples/codex_mcp_config.toml").read_text(encoding="utf-8")
    codex_preview = Path("examples/codex_preview_mcp_config.toml").read_text(encoding="utf-8")
    workflow = Path("examples/first_preview_workflow.md").read_text(encoding="utf-8")

    required_terms = [
        "PyPI",
        "MCP Registry",
        "Claude Desktop",
        "Claude Code",
        "Cursor",
        "Codex",
        "--allowed-root",
        "--artifact-root",
        "Smoke Check",
        "Troubleshooting",
    ]

    assert "[docs/INSTALL.md](docs/INSTALL.md)" in readme
    assert "[INSTALL.md](INSTALL.md)" in usage
    for term in required_terms:
        assert term in install
    for config in [claude_pypi, claude_preview, cursor, cursor_preview]:
        server = config["mcpServers"]["albumentationsx"]
        assert server["command"] == "uvx"
        assert server["args"][:3] == ["--from", "albumentationsx-mcp", "albumentationsx-mcp"]
    for config in [claude_preview, cursor_preview]:
        args = config["mcpServers"]["albumentationsx"]["args"]
        assert "--allowed-root" in args
        assert "--artifact-root" in args
    assert 'command = "uvx"' in codex
    assert 'args = ["--from", "albumentationsx-mcp", "albumentationsx-mcp"]' in codex
    assert "--allowed-root" in codex_preview
    assert "--artifact-root" in codex_preview
    assert "Claude Desktop" in workflow
    assert "Claude Code" in workflow
    assert "Cursor" in workflow
    assert "Codex" in workflow
    assert "validate_preview_request" in workflow


def test_docs_link_client_smoke_playbook_resource() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    install = Path("docs/INSTALL.md").read_text(encoding="utf-8")
    usage = Path("docs/USAGE.md").read_text(encoding="utf-8")
    recipes = Path("docs/RECIPES.md").read_text(encoding="utf-8")

    for content in [install, usage, recipes]:
        assert "albumentationsx://examples/client-smoke" in content
        assert "albumentationsx://examples/first-preview" in content
        assert "albumentationsx://examples/distortion-review" in content
        assert "validate_preview_request" in content
    assert "run_first_preview_review" in install
    assert "run_first_preview_review" in usage
    for content in [readme, install, usage, recipes]:
        assert "run_host_smoke_check" in content
        assert "preview_ready" in content
        assert "preview_request_template" in content
    for content in [readme, install, usage]:
        assert "when the host exposes resource reads" in content.lower()
        assert "otherwise call `run_host_smoke_check` directly" in content.lower()
    assert "client smoke" in install.lower()
    assert "client-smoke" in usage
    assert "client-smoke" in recipes


def test_host_acceptance_checklist_covers_registry_and_hosts() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    checklist = Path("docs/HOST_ACCEPTANCE.md").read_text(encoding="utf-8")
    matrix = Path("docs/HOST_MATRIX.md").read_text(encoding="utf-8")
    evidence = Path("docs/HOST_ACCEPTANCE_EVIDENCE.md").read_text(encoding="utf-8")
    manual_runs = Path("docs/HOST_MANUAL_RUNS.json").read_text(encoding="utf-8")
    manual_runs_schema = json.loads(Path("docs/HOST_MANUAL_RUNS.schema.json").read_text(encoding="utf-8"))

    assert "[docs/HOST_ACCEPTANCE.md](docs/HOST_ACCEPTANCE.md)" in readme
    assert "[docs/HOST_MATRIX.md](docs/HOST_MATRIX.md)" in readme
    assert "[docs/HOST_ACCEPTANCE_EVIDENCE.md](docs/HOST_ACCEPTANCE_EVIDENCE.md)" in readme
    assert "Operational scripts live in [scripts](scripts/)" in readme
    host_scripts = [
        "export_host_acceptance_report.py",
        "export_manual_host_acceptance_packet.py",
        "validate_host_manual_runs.py",
        "record_host_manual_run.py",
    ]
    for script in host_scripts:
        assert script in checklist
    for script in ["export_host_acceptance_report.py", "export_manual_host_acceptance_packet.py"]:
        assert script in matrix
    assert "[HOST_MATRIX.md](HOST_MATRIX.md)" in checklist
    assert "MCP Registry card" in checklist
    assert "io.github.dKosarevsky/albu-mcp" in checklist
    assert "https://avatars.githubusercontent.com/u/57894582?s=200&v=4" in checklist
    assert "Claude Desktop" in checklist
    assert "Claude Code" in checklist
    assert "Cursor" in checklist
    assert "Codex" in checklist
    assert "run_host_smoke_check" in checklist
    assert "validate_preview_request" in checklist
    assert "render_preview_batch" in checklist
    assert "start_tuning_session" in checklist
    assert "record_tuning_session_step" in checklist
    assert "close_tuning_session" in checklist
    assert "export_tuning_session" in checklist
    for host in ["Claude Desktop", "Claude Code", "Cursor", "Codex"]:
        assert host in matrix
    for term in ["close_tuning_session", "archive_tuning_session", "cleanup_tuning_sessions"]:
        assert term in matrix
    assert "Manual Host UI: blocked" in evidence
    assert "Manual Host UI: passed" not in evidence
    assert '"status": "blocked"' in manual_runs
    assert '"host": "Codex"' in manual_runs
    assert "Claude Desktop" in manual_runs_schema["properties"]["manual_host_ui"]["items"]["properties"]["host"]["enum"]
    assert "blocked" in manual_runs_schema["properties"]["manual_host_ui"]["items"]["properties"]["status"]["enum"]
    assert "HOST_MANUAL_RUNS.json" in checklist
    assert "HOST_MANUAL_RUNS.schema.json" in checklist
    assert "HOST_MANUAL_RUNS.json" in matrix
    assert "HOST_MANUAL_RUNS.schema.json" in matrix
    release_docs = Path("docs/RELEASE.md").read_text(encoding="utf-8")
    for script in host_scripts:
        assert script in release_docs
    assert "HOST_MANUAL_RUNS.json" in release_docs


def test_strict_manual_host_acceptance_gate_is_documented() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    checklist = Path("docs/HOST_ACCEPTANCE.md").read_text(encoding="utf-8")
    release_docs = Path("docs/RELEASE.md").read_text(encoding="utf-8")

    assert "Operational scripts live in [scripts](scripts/)" in readme
    for content in [checklist, release_docs]:
        assert "check_manual_host_acceptance.py" in content
    assert "fails while any required host is missing" in checklist


def test_host_acceptance_freshness_guard_is_documented() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    checklist = Path("docs/HOST_ACCEPTANCE.md").read_text(encoding="utf-8")
    matrix = Path("docs/HOST_MATRIX.md").read_text(encoding="utf-8")
    release_docs = Path("docs/RELEASE.md").read_text(encoding="utf-8")

    for content in [readme, checklist, matrix, release_docs]:
        assert "check_host_acceptance_report.py" in content
    for content in [checklist, matrix, release_docs]:
        assert "generated evidence freshness guard" in content


def test_contract_snapshot_freshness_guard_is_documented() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    compatibility = Path("docs/COMPATIBILITY.md").read_text(encoding="utf-8")
    release_docs = Path("docs/RELEASE.md").read_text(encoding="utf-8")

    for content in [readme, compatibility, release_docs]:
        assert "check_contract_snapshots.py" in content
    for content in [compatibility, release_docs]:
        assert "classify_contract_drift.py" in content
    assert "contract snapshot freshness guard" in compatibility
    assert "structured snapshot drift classifier" in release_docs


def test_release_readiness_guard_is_documented() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    release_docs = Path("docs/RELEASE.md").read_text(encoding="utf-8")
    audit = Path("docs/V1_READINESS.md").read_text(encoding="utf-8")

    for content in [readme, release_docs, audit]:
        assert "check_release_readiness.py" in content
    assert "release readiness guard" in release_docs
    assert "--format json" in release_docs
    assert "GITHUB_STEP_SUMMARY" in release_docs


def test_docs_link_diagnostics_playbook_resource() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    install = Path("docs/INSTALL.md").read_text(encoding="utf-8")
    usage = Path("docs/USAGE.md").read_text(encoding="utf-8")
    recipes = Path("docs/RECIPES.md").read_text(encoding="utf-8")

    for content in [readme, install, usage, recipes]:
        assert "albumentationsx://diagnostics/guide" in content
        assert "diagnose_environment" in content
    assert "remediation_actions" in install
    assert "remediation_actions" in usage
    assert "fix_allowed_root" in usage
    assert "albumentationsx://examples/diagnostics" in usage
    assert "albumentationsx://examples/diagnostics" in recipes


def test_v1_readiness_audit_is_present_and_complete() -> None:
    audit = Path("docs/V1_READINESS.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")

    required_terms = [
        "Public Contract Freeze",
        "Snapshot Guards",
        "Golden Evals",
        "Release Automation",
        "Install Flow",
        "Compatibility Policy",
        "Current Status",
        "build_review_packet",
        "v1.0.0",
    ]

    for term in required_terms:
        assert term in audit
    assert "[docs/V1_READINESS.md](docs/V1_READINESS.md)" in readme


def test_release_docs_and_package_metadata_are_v1_ready() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    release_docs = Path("docs/RELEASE.md").read_text(encoding="utf-8")

    assert '"Development Status :: 5 - Production/Stable"' in pyproject
    assert '"Development Status :: 3 - Alpha"' not in pyproject
    assert "v0.1.0" not in release_docs
    assert "vX.Y.Z" in release_docs
    assert "CHANGELOG.md" in release_docs
    assert "README.md" in release_docs
    assert "server.json" in release_docs
    assert "uv.lock" in release_docs


def test_changelog_tracks_public_releases_and_next_features() -> None:
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "## 0.2.1" in changelog
    assert "## 0.2.0" in changelog
    assert "## 0.1.0" in changelog
    assert "demo" in changelog.lower()
    assert "mcp registry" in changelog.lower()
    assert "feedback severity" in changelog.lower()


def test_release_workflow_and_readme_publish_instructions_are_present() -> None:
    release_workflow = Path(".github/workflows/release.yml")
    readme = Path("README.md").read_text(encoding="utf-8")
    release_docs = Path("docs/RELEASE.md")

    assert release_workflow.exists()
    workflow = yaml.safe_load(release_workflow.read_text(encoding="utf-8"))
    build_steps = workflow["jobs"]["build"]["steps"]
    release_steps = workflow["jobs"]["github-release"]["steps"]
    build_commands = "\n".join(step.get("run", "") for step in build_steps)
    release_commands = "\n".join(step.get("run", "") for step in release_steps)
    mcp_registry_commands = "\n".join(step.get("run", "") for step in workflow["jobs"]["publish-mcp-registry"]["steps"])
    assert "uv build" in build_commands
    assert (
        'python scripts/extract_release_notes.py --tag "${GITHUB_REF_NAME}" --output release-notes.md' in build_commands
    )
    assert any(
        "actions/upload-artifact" in step.get("uses", "") and step.get("with", {}).get("name") == "release-notes"
        for step in build_steps
    )
    assert any(
        "actions/download-artifact" in step.get("uses", "") and step.get("with", {}).get("name") == "release-notes"
        for step in release_steps
    )
    assert "uv run python scripts/validate_host_manual_runs.py" in build_commands
    assert "uv run python scripts/check_host_acceptance_report.py" in build_commands
    assert "uv run python scripts/check_contract_snapshots.py" in build_commands
    assert "uv run python scripts/check_demo_assets.py --output-dir docs/assets/demo --check" in build_commands
    assert 'uv run python scripts/check_release_readiness.py --tag "${GITHUB_REF_NAME}"' in build_commands
    assert "--notes-file" in release_commands
    assert "--generate-notes" not in release_commands
    assert "gh release create" in release_commands
    assert workflow["jobs"]["publish-mcp-registry"]["needs"] == "post-release-smoke"
    assert "mcp-publisher publish" in mcp_registry_commands
    assert "cannot publish duplicate version" in mcp_registry_commands
    assert "python scripts/check_mcp_registry_status.py" in mcp_registry_commands
    assert "uvx --from albumentationsx-mcp albumentationsx-mcp" in readme
    assert "uv publish --trusted-publishing automatic" in release_docs.read_text(encoding="utf-8")


def test_manual_mcp_publish_workflow_uses_registry_status_guard() -> None:
    workflow = yaml.safe_load(Path(".github/workflows/publish-mcp.yml").read_text(encoding="utf-8"))
    commands = "\n".join(step.get("run", "") for step in workflow["jobs"]["publish"]["steps"])

    assert "mcp-publisher publish" in commands
    assert "cannot publish duplicate version" in commands
    assert "python scripts/check_mcp_registry_status.py" in commands


def test_release_workflow_publishes_to_pypi_with_trusted_publishing() -> None:
    workflow = yaml.safe_load(Path(".github/workflows/release.yml").read_text(encoding="utf-8"))
    publish_job = workflow["jobs"]["publish-pypi"]
    release_job = workflow["jobs"]["github-release"]
    publish_commands = "\n".join(step.get("run", "") for step in publish_job["steps"])

    assert publish_job["needs"] == "build"
    assert publish_job["environment"]["name"] == "pypi"
    assert publish_job["environment"]["url"] == "https://pypi.org/project/albumentationsx-mcp/"
    assert publish_job["permissions"]["id-token"] == "write"
    assert publish_job["permissions"]["contents"] == "read"
    assert "uv publish --trusted-publishing automatic dist/*" in publish_commands
    assert release_job["needs"] == "publish-pypi"
    assert release_job["permissions"]["contents"] == "write"


def test_release_workflow_publishes_isolated_mcpb_artifact() -> None:
    workflow = yaml.safe_load(Path(".github/workflows/release.yml").read_text(encoding="utf-8"))
    build_steps = workflow["jobs"]["build"]["steps"]
    publish_steps = workflow["jobs"]["publish-pypi"]["steps"]
    release_steps = workflow["jobs"]["github-release"]["steps"]
    build_commands = "\n".join(step.get("run", "") for step in build_steps)
    publish_commands = "\n".join(step.get("run", "") for step in publish_steps)
    release_commands = "\n".join(step.get("run", "") for step in release_steps)

    setup_node = next(step for step in build_steps if step.get("uses", "").startswith("actions/setup-node@"))
    python_upload = next(
        step
        for step in build_steps
        if step.get("uses", "").startswith("actions/upload-artifact@") and step.get("with", {}).get("name") == "dist"
    )
    mcpb_upload = next(
        step
        for step in build_steps
        if step.get("uses", "").startswith("actions/upload-artifact@") and step.get("with", {}).get("name") == "mcpb"
    )
    release_downloads = [
        step for step in release_steps if step.get("uses", "").startswith("actions/download-artifact@")
    ]

    assert setup_node["with"]["node-version"] == "24"
    assert "uv run python scripts/check_desktop_extension.py" in build_commands
    assert "uv run python -m scripts.build_desktop_extension --output-dir dist/mcpb" in build_commands
    assert "cd dist/mcpb && sha256sum *.mcpb > SHA256SUMS" in build_commands
    assert python_upload["with"]["path"] == "dist/*.whl\ndist/*.tar.gz\n"
    assert mcpb_upload["with"]["path"] == "dist/mcpb/*"
    assert "uv publish --trusted-publishing automatic dist/*" in publish_commands
    assert ".mcpb" not in publish_commands
    assert any(
        step.get("with", {}).get("name") == "dist" and step.get("with", {}).get("path") == "dist/python"
        for step in release_downloads
    )
    assert any(
        step.get("with", {}).get("name") == "mcpb" and step.get("with", {}).get("path") == "dist/mcpb"
        for step in release_downloads
    )
    assert "dist/python/* dist/mcpb/*" in release_commands


def test_release_docs_cover_mcpb_artifact_flow() -> None:
    release_docs = Path("docs/RELEASE.md").read_text(encoding="utf-8")

    for term in [
        "desktop-extension/manifest.json",
        "scripts/check_desktop_extension.py",
        "scripts.build_desktop_extension",
        "albumentationsx-mcp-<version>.mcpb",
        "SHA256SUMS",
        "separate workflow artifact",
        "never published to PyPI",
    ]:
        assert term in release_docs


def test_public_package_metadata_is_polished() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "https://img.shields.io/pypi/v/albumentationsx-mcp" in readme
    assert "https://pypi.org/project/albumentationsx-mcp/" in readme
    assert "MCP%20Registry-active-green" in readme
    assert "https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.dKosarevsky/albu-mcp" in readme
    assert "[server.json](server.json): public MCP Registry metadata." in readme
    assert "[project.urls]" in pyproject
    assert '"Repository" = "https://github.com/dKosarevsky/albu-mcp"' in pyproject
    assert '"Documentation" = "https://github.com/dKosarevsky/albu-mcp/blob/main/docs/USAGE.md"' in pyproject
    assert (
        '"MCP Registry" = "https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.dKosarevsky/albu-mcp"'
        in pyproject
    )
    assert '"Development Status :: 5 - Production/Stable"' in pyproject
    assert '"Framework :: Pytest"' in pyproject
    assert '"Topic :: Scientific/Engineering :: Artificial Intelligence"' in pyproject


def test_upstream_pr_packet_is_available() -> None:
    packet_path = Path("docs/UPSTREAM_PR_PACKET.md")
    readme = Path("README.md").read_text(encoding="utf-8")
    network_growth = Path("docs/NETWORK_GROWTH.md").read_text(encoding="utf-8")

    assert packet_path.exists()
    packet = packet_path.read_text(encoding="utf-8")

    assert "https://github.com/albumentations-team/AlbumentationsX/issues/285" in packet
    assert "Accepted Upstream Snippet" in packet
    assert "Community integration" in packet
    assert "segmentation mask onboarding" in packet
    assert "not an official AlbumentationsX project" in packet
    assert "docs/UPSTREAM_PR_PACKET.md" in readme
    assert "docs/UPSTREAM_PR_PACKET.md" in network_growth


def test_public_docs_describe_current_preview_workflow() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    usage = Path("docs/USAGE.md").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    server_json = json.loads(Path("server.json").read_text(encoding="utf-8"))

    assert len(readme.splitlines()) <= 130
    assert "## What Changed In" not in readme
    assert "[CHANGELOG.md](CHANGELOG.md)" in readme
    assert "## 0.2.0" in changelog
    assert "## 0.3.0" in changelog
    assert "## 0.4.0" in changelog
    assert "quality_summary" in usage
    assert "too_noisy:high" in readme
    assert "suggested_feedback_tags" in usage
    assert "exposure_too_weak:medium" in readme
    assert "one real local image or an image directory" in usage
    assert "validate_preview_request" in readme
    assert "validate_preview_request" in usage
    assert "docs/RECIPES.md" in readme
    assert "batch previews" in readme
    assert "compare preview runs" in readme
    assert "agent workflow resources" in readme.lower()
    assert "batch previews" in server_json["description"]
    assert "compare preview runs" in server_json["description"]
    assert "segmentation masks" in server_json["description"]


def test_readme_operator_cli_section_stays_concise() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    usage = Path("docs/USAGE.md").read_text(encoding="utf-8")
    operator_section = readme.split("## Operator CLI", 1)[1].split("## Host Workflow", 1)[0]

    assert len(operator_section.splitlines()) <= 18
    assert operator_section.count("albu-mcp ") <= 8
    assert "[docs/USAGE.md](docs/USAGE.md)" in operator_section
    assert "[CHANGELOG.md](CHANGELOG.md)" in readme
    assert "albu-mcp host setup-probe" in operator_section
    assert "albu-mcp preview first-pack" in operator_section
    assert "albu-mcp evidence collect" in operator_section
    assert "albu-mcp beta loop-pack" in operator_section
    assert "albu-mcp evidence import-artifacts" in usage


def test_codex_plugin_bundle_has_concise_public_setup_guidance() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    install = Path("docs/INSTALL.md").read_text(encoding="utf-8")

    assert "native Codex plugin bundle" in readme
    expected_install_text = [
        ".codex-plugin/plugin.json",
        ".mcp.json",
        "loads the canonical skill and the pinned base MCP server together",
        "does not grant a user dataset",
        "ALBU_MCP_ALLOWED_ROOTS",
        "ALBU_MCP_ARTIFACT_ROOT",
        "ALBU_MCP_MAX_PREVIEW_RUNS",
        "Restart Codex",
        "run_host_smoke_check",
        "`allowed_roots` contains the intended dataset root",
        "Direct TOML configuration remains the fallback",
        "not a public Codex marketplace listing",
    ]
    for expected_text in expected_install_text:
        assert expected_text in install


def test_release_workflow_checks_versions_and_smokes_published_package() -> None:
    workflow = yaml.safe_load(Path(".github/workflows/release.yml").read_text(encoding="utf-8"))
    build_commands = "\n".join(step.get("run", "") for step in workflow["jobs"]["build"]["steps"])
    smoke_job = workflow["jobs"]["post-release-smoke"]
    smoke_commands = "\n".join(step.get("run", "") for step in smoke_job["steps"])

    assert Path("scripts/check_release_version.py").exists()
    assert Path("scripts/check_published_package_smoke.py").exists()
    assert "uv run python scripts/check_release_version.py" in build_commands
    assert smoke_job["needs"] == "github-release"
    assert any(step.get("uses") == "actions/checkout@v5" for step in smoke_job["steps"])
    assert 'python scripts/check_published_package_smoke.py --version "${GITHUB_REF_NAME#v}"' in smoke_commands
    assert "for attempt in" not in smoke_commands
    assert 'uvx --from "albumentationsx-mcp==${GITHUB_REF_NAME#v}"' not in smoke_commands


def test_mcp_registry_metadata_is_ready_for_pypi_distribution() -> None:
    server_json = json.loads(Path("server.json").read_text(encoding="utf-8"))
    readme = Path("README.md").read_text(encoding="utf-8")

    assert server_json["name"] == "io.github.dKosarevsky/albu-mcp"
    assert server_json["websiteUrl"] == "https://github.com/dKosarevsky/albu-mcp#readme"
    assert len(server_json["description"]) <= 100
    assert server_json["repository"] == {
        "url": "https://github.com/dKosarevsky/albu-mcp",
        "source": "github",
        "id": "1268159067",
    }
    assert server_json["icons"] == [
        {
            "src": "https://avatars.githubusercontent.com/u/57894582?s=200&v=4",
            "mimeType": "image/png",
            "sizes": ["200x200"],
        },
    ]
    assert server_json["packages"][0]["registryType"] == "pypi"
    assert server_json["packages"][0]["identifier"] == "albumentationsx-mcp"
    assert server_json["packages"][0]["transport"]["type"] == "stdio"
    assert "<!-- mcp-name: io.github.dKosarevsky/albu-mcp -->" in readme


def test_mcp_registry_publish_workflow_is_present() -> None:
    workflow_path = Path(".github/workflows/publish-mcp.yml")
    registry_guard = Path("scripts/check_mcp_registry_status.py").read_text(encoding="utf-8")
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["publish"]["steps"]
    commands = "\n".join(step.get("run", "") for step in steps)

    assert workflow["jobs"]["publish"]["permissions"]["id-token"] == "write"
    assert "mcp-publisher login github-oidc" in commands
    assert "mcp-publisher publish" in commands
    assert "cannot publish duplicate version" in commands
    assert "python scripts/check_mcp_registry_status.py" in commands
    assert "registry.modelcontextprotocol.io/v0.1/servers" in registry_guard
