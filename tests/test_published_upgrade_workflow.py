import json
import sys
from pathlib import Path
from typing import cast

import pytest
import yaml

from albumentationsx_mcp.upgrade_proof import validate_upgrade_proof_report

_EVIDENCE = Path("docs/host-evidence/published-upgrade-1.20.0-to-1.21.0-2026-08-04.json")
_STATUS = Path("docs/STATUS.md")
_WORKFLOW = Path(".github/workflows/published-upgrade-proof.yml")
_PROOF_COMMAND = (
    'uv run python scripts/check_published_upgrade.py --from-version "$FROM_VERSION" '
    '--to-version "$TO_VERSION" --observed-on "$(date -u +%F)" '
    "--output artifacts/published-upgrade-proof.json"
)
_STEP_NAMES = [
    "Check out repository",
    "Install uv",
    "Set up Python",
    "Install current client and probe dependencies",
    "Prepare artifact directory",
    "Prove published upgrade",
    "Upload privacy-safe evidence",
]


def _load_workflow() -> tuple[str, dict[object, object]]:
    text = _WORKFLOW.read_text(encoding="utf-8")
    workflow = yaml.safe_load(text)
    assert isinstance(workflow, dict)
    return text, workflow


def _job(workflow: dict[object, object]) -> dict[object, object]:
    raw_jobs = workflow["jobs"]
    assert isinstance(raw_jobs, dict)
    jobs = cast("dict[object, object]", raw_jobs)
    assert list(jobs) == ["prove-upgrade"]
    job = jobs["prove-upgrade"]
    assert isinstance(job, dict)
    return cast("dict[object, object]", job)


def _steps(workflow: dict[object, object]) -> list[dict[object, object]]:
    raw_steps = _job(workflow)["steps"]
    assert isinstance(raw_steps, list)
    steps: list[dict[object, object]] = []
    for step in raw_steps:
        assert isinstance(step, dict)
        steps.append(cast("dict[object, object]", step))
    return steps


def _is_upload_step(step: dict[object, object]) -> bool:
    uses = step.get("uses")
    return isinstance(uses, str) and uses.startswith("actions/upload-artifact@")


def _github_expressions(
    value: object,
    path: tuple[object, ...] = (),
) -> list[tuple[tuple[object, ...], str]]:
    if isinstance(value, str):
        return [(path, value)] if "${{" in value else []
    if isinstance(value, dict):
        expressions: list[tuple[tuple[object, ...], str]] = []
        for key, nested_value in cast("dict[object, object]", value).items():
            expressions.extend(_github_expressions(nested_value, (*path, key)))
        return expressions
    if isinstance(value, list):
        expressions = []
        for index, nested_value in enumerate(cast("list[object]", value)):
            expressions.extend(_github_expressions(nested_value, (*path, index)))
        return expressions
    return []


def test_published_upgrade_workflow_is_manual_and_least_privilege() -> None:
    text, workflow = _load_workflow()
    triggers = workflow.get("on", workflow.get(True))

    assert triggers == {
        "workflow_dispatch": {
            "inputs": {
                "from_version": {
                    "description": "Published version to upgrade from",
                    "required": True,
                    "default": "1.20.0",
                    "type": "string",
                },
                "to_version": {
                    "description": "Published version to upgrade to",
                    "required": True,
                    "default": "1.21.0",
                    "type": "string",
                },
            }
        }
    }
    assert workflow["permissions"] == {"contents": "read"}
    for dangerous_trigger in [
        "pull_request:",
        "push:",
        "schedule:",
        "workflow_call:",
        "repository_dispatch:",
    ]:
        assert dangerous_trigger not in text
    assert "secrets." not in text
    assert "id-token:" not in text


def test_published_upgrade_workflow_has_one_bounded_ubuntu_job() -> None:
    _, workflow = _load_workflow()

    job = _job(workflow)
    assert job["runs-on"] == "ubuntu-latest"
    assert job["timeout-minutes"] == 20
    assert "permissions" not in job


def _assert_published_upgrade_workflow_prepares_and_runs_probe_safely() -> None:
    _, workflow = _load_workflow()
    steps = _steps(workflow)
    assert [step["name"] for step in steps] == _STEP_NAMES
    named_steps = {step["name"]: step for step in steps}

    assert named_steps["Check out repository"] == {
        "name": "Check out repository",
        "uses": "actions/checkout@v5",
        "with": {"persist-credentials": False},
    }
    assert named_steps["Install uv"] == {
        "name": "Install uv",
        "uses": "astral-sh/setup-uv@v7",
        "with": {"enable-cache": False},
    }
    assert named_steps["Set up Python"] == {
        "name": "Set up Python",
        "uses": "actions/setup-python@v6",
        "with": {"python-version": "3.13"},
    }
    assert named_steps["Install current client and probe dependencies"]["run"] == "uv sync --frozen --dev"

    prepare = named_steps["Prepare artifact directory"]
    prove = named_steps["Prove published upgrade"]
    assert prepare["run"] == "install -d -m 700 artifacts"
    assert steps.index(prepare) < steps.index(prove)
    assert prove["env"] == {
        "FROM_VERSION": "${{ inputs.from_version }}",
        "TO_VERSION": "${{ inputs.to_version }}",
    }
    prove_command = prove["run"]
    assert isinstance(prove_command, str)
    assert " ".join(prove_command.split()) == _PROOF_COMMAND
    assert "continue-on-error" not in prove
    for step in steps:
        run = step.get("run")
        assert run is None or isinstance(run, str)
        assert "${{" not in (run or "")
    assert _github_expressions(workflow) == [
        (
            ("jobs", "prove-upgrade", "steps", 5, "env", "FROM_VERSION"),
            "${{ inputs.from_version }}",
        ),
        (
            ("jobs", "prove-upgrade", "steps", 5, "env", "TO_VERSION"),
            "${{ inputs.to_version }}",
        ),
    ]


def test_published_upgrade_workflow_prepares_and_runs_probe_safely() -> None:
    _assert_published_upgrade_workflow_prepares_and_runs_probe_safely()


def _assert_workflow_variant_is_rejected(
    unsafe_workflow: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unsafe_path = tmp_path / "published-upgrade-proof.yml"
    unsafe_path.write_text(unsafe_workflow, encoding="utf-8")
    monkeypatch.setattr(sys.modules[__name__], "_WORKFLOW", unsafe_path)

    with pytest.raises(AssertionError):
        _assert_published_upgrade_workflow_prepares_and_runs_probe_safely()


def test_published_upgrade_workflow_contract_rejects_github_expression_in_any_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workflow = _WORKFLOW.read_text(encoding="utf-8")
    action = "        uses: actions/upload-artifact@v7\n"
    unsafe_workflow = workflow.replace(
        action,
        action + '        run: echo "${{ github.event.inputs.from_version }}"\n',
        1,
    )
    assert unsafe_workflow != workflow

    _assert_workflow_variant_is_rejected(unsafe_workflow, tmp_path, monkeypatch)


def test_published_upgrade_workflow_contract_rejects_encoded_job_expression(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workflow = _WORKFLOW.read_text(encoding="utf-8")
    timeout = "    timeout-minutes: 20\n"
    encoded_env = '    env:\n      BASH_ENV: "\\u0024{{ inputs.from_version }}"\n'
    unsafe_workflow = workflow.replace(timeout, timeout + encoded_env, 1)
    assert unsafe_workflow != workflow

    _assert_workflow_variant_is_rejected(unsafe_workflow, tmp_path, monkeypatch)


def test_published_upgrade_workflow_contract_rejects_unreviewed_steps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workflow = _WORKFLOW.read_text(encoding="utf-8")
    marker = "      - name: Upload privacy-safe evidence\n"
    extra_step = "      - name: Unreviewed action\n        uses: example/unreviewed-action@v1\n\n"
    unsafe_workflow = workflow.replace(marker, extra_step + marker, 1)
    assert unsafe_workflow != workflow

    _assert_workflow_variant_is_rejected(unsafe_workflow, tmp_path, monkeypatch)


def test_published_upgrade_workflow_uploads_only_successful_evidence() -> None:
    _, workflow = _load_workflow()
    steps = _steps(workflow)
    upload_steps = [step for step in steps if _is_upload_step(step)]

    assert upload_steps == [
        {
            "name": "Upload privacy-safe evidence",
            "uses": "actions/upload-artifact@v7",
            "with": {
                "name": "published-upgrade-proof",
                "path": "artifacts/published-upgrade-proof.json",
                "if-no-files-found": "error",
                "retention-days": 30,
            },
        }
    ]
    prove_index = next(index for index, step in enumerate(steps) if step["name"] == "Prove published upgrade")
    assert steps.index(upload_steps[0]) > prove_index


def test_committed_upgrade_evidence_is_passing_and_privacy_safe() -> None:
    content = _EVIDENCE.read_text(encoding="utf-8")
    report = json.loads(content)
    validated = validate_upgrade_proof_report(
        report,
        expected_package="albumentationsx-mcp",
        expected_from_version="1.20.0",
        expected_to_version="1.21.0",
        expected_observed_on="2026-08-04",
    )

    assert validated == report
    assert validated["status"] == "pass"
    assert validated["from_version"] == "1.20.0"
    assert validated["to_version"] == "1.21.0"
    assert validated["observed_on"] == "2026-08-04"
    assert [row["role"] for row in validated["matrix"]] == ["from_legacy", "to_legacy", "to_modern"]
    assert all(row["ok"] and row["protocol_ok"] and row["server_version_ok"] for row in validated["matrix"])

    compatibility = validated["compatibility"]
    assert compatibility["old_surface_is_subset"] is True
    assert compatibility["new_modes_equal"] is True
    assert compatibility["categories"]["prompts"]["ok"] is True
    assert compatibility["categories"]["resource_templates"]["ok"] is True
    assert compatibility["categories"]["resources"]["ok"] is True
    assert compatibility["categories"]["tools"]["ok"] is True

    artifact = validated["artifact_continuity"]
    assert artifact["ok"] is True
    assert all(
        artifact[field] is True
        for field in (
            "manifest_readable",
            "contact_sheet_readable",
            "manifest_run_id_matches",
            "content_unchanged",
        )
    )
    assert validated["failures"] == []

    lowered = content.casefold()
    for private_marker in (
        "/users/",
        "/home/",
        "\\users\\",
        "albu_mcp_",
        "token",
        "authorization",
        "bearer ",
        "api_key",
        "api-key",
        "password",
        "passwd",
        "secret",
        "private_key",
        "private-key",
        "access_key",
        "access-key",
        "begin rsa private key",
        "begin openssh private key",
    ):
        assert private_marker not in lowered


def test_status_links_the_published_upgrade_evidence_with_machine_only_scope() -> None:
    status = _STATUS.read_text(encoding="utf-8")

    assert (
        "Evidence: [privacy-safe machine report](host-evidence/published-upgrade-1.20.0-to-1.21.0-2026-08-04.json)"
    ) in status
    assert (
        "Scope: Streamable HTTP conformance and published-package artifact continuity. "
        "This is not real-host UI evidence."
    ) in status
