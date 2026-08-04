import hashlib
import json
import re
import sys
from collections.abc import Mapping
from pathlib import Path, PureWindowsPath
from typing import cast
from urllib.parse import urlsplit

import pytest
import yaml

from albumentationsx_mcp.upgrade_proof import parse_upgrade_proof_report, serialize_upgrade_proof_report

_EVIDENCE = Path("docs/host-evidence/published-upgrade-1.20.0-to-1.21.0-2026-08-04.json")
_GIT_ATTRIBUTES = Path(".gitattributes")
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
_NORMALIZED_SENSITIVE_KEYS = frozenset(
    {
        "access_key",
        "access_token",
        "account_name",
        "api_key",
        "auth_token",
        "authorization",
        "aws_access_key_id",
        "client_secret",
        "computer_name",
        "credential",
        "credentials",
        "device_id",
        "device_name",
        "host_id",
        "host_name",
        "hostname",
        "machine_guid",
        "machine_id",
        "machine_name",
        "password",
        "passwd",
        "private_key",
        "refresh_token",
        "secret",
        "session_id",
        "token",
        "user_name",
        "username",
    }
)
_NORMALIZED_CREDENTIAL_SUFFIXES = (
    "_access_key",
    "_access_key_id",
    "_api_key",
    "_credential",
    "_credentials",
    "_password",
    "_passwd",
    "_private_key",
    "_secret",
    "_token",
)
_NORMALIZED_MACHINE_ENV_NAMES = frozenset(
    {
        "computername",
        "home",
        "homedrive",
        "homepath",
        "hostname",
        "logname",
        "oldpwd",
        "path",
        "pwd",
        "shell",
        "temp",
        "tmp",
        "tmpdir",
        "user",
        "userdomain",
        "username",
        "userprofile",
    }
)
_ENV_NAME = re.compile(r"[A-Z][A-Z0-9_]*\Z")
_ENV_REFERENCE = re.compile(r"(?:\$[A-Z][A-Z0-9_]*|\$\{[A-Z][A-Z0-9_]*\}|%[A-Z][A-Z0-9_]*%)")


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


def _normalize_key(key: str) -> str:
    acronym_separated = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", key)
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", acronym_separated)
    return re.sub(r"[^a-zA-Z0-9]+", "_", separated).strip("_").casefold()


def _is_sensitive_key(key: str) -> bool:
    normalized = _normalize_key(key)
    if normalized in _NORMALIZED_SENSITIVE_KEYS or normalized.startswith("albu_mcp_"):
        return True
    if normalized.endswith(_NORMALIZED_CREDENTIAL_SUFFIXES):
        return True
    return _ENV_NAME.fullmatch(key) is not None and normalized in _NORMALIZED_MACHINE_ENV_NAMES


def _is_private_string(value: str) -> bool:
    candidate = value.strip()
    windows_path = PureWindowsPath(candidate)
    if candidate.startswith("/") or windows_path.root:
        return True
    if candidate.casefold().startswith("file:") or _ENV_REFERENCE.search(candidate) is not None:
        return True
    parsed = urlsplit(candidate)
    if parsed.username is not None or parsed.password is not None:
        return True
    return "-----BEGIN " in candidate.upper() and " PRIVATE KEY-----" in candidate.upper()


def _assert_evidence_privacy_safe(value: object) -> None:
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            assert isinstance(key, str)
            assert not _is_sensitive_key(key)
            _assert_evidence_privacy_safe(nested_value)
    elif isinstance(value, list):
        for item in value:
            _assert_evidence_privacy_safe(item)
    elif isinstance(value, str):
        assert not _is_private_string(value)


def _assert_committed_upgrade_evidence(path: Path) -> None:
    raw_content = path.read_bytes()
    validated = parse_upgrade_proof_report(
        raw_content,
        expected_package="albumentationsx-mcp",
        expected_from_version="1.20.0",
        expected_to_version="1.21.0",
        expected_observed_on="2026-08-04",
    )

    assert raw_content == serialize_upgrade_proof_report(validated).encode("utf-8")
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
    _assert_evidence_privacy_safe(validated)


def test_committed_upgrade_evidence_is_passing_and_privacy_safe() -> None:
    _assert_committed_upgrade_evidence(_EVIDENCE)


@pytest.mark.parametrize("mutation", ["duplicate_status", "noncanonical_format", "crlf"])
def test_committed_upgrade_evidence_rejects_noncanonical_json(mutation: str, tmp_path: Path) -> None:
    content = _EVIDENCE.read_bytes()
    if mutation == "duplicate_status":
        mutated = content.replace(b'  "status": "pass",', b'  "status": "pass",\n  "status": "pass",', 1)
    elif mutation == "noncanonical_format":
        mutated = (json.dumps(json.loads(content), sort_keys=True) + "\n").encode()
    else:
        mutated = content.replace(b"\n", b"\r\n")
    assert mutated != content
    evidence = tmp_path / "published-upgrade.json"
    evidence.write_bytes(mutated)

    with pytest.raises(ValueError, match=r"^published upgrade proof report is invalid$"):
        _assert_committed_upgrade_evidence(evidence)


def test_committed_upgrade_evidence_is_forced_to_lf_on_checkout() -> None:
    assert _GIT_ATTRIBUTES.exists()
    assert _GIT_ATTRIBUTES.read_text(encoding="utf-8") == (
        "docs/host-evidence/published-upgrade-1.20.0-to-1.21.0-2026-08-04.json text eol=lf\n"
        "docs/host-evidence/profile-conformance-2026-08-04.json text eol=lf\n"
    )


@pytest.mark.parametrize(
    "private_value",
    [
        pytest.param({"detail": "/private/var/folders/proof.json"}, id="private-posix-path"),
        pytest.param({"detail": "/var/tmp/proof.json"}, id="var-posix-path"),  # noqa: S108
        pytest.param({"detail": "/tmp/proof.json"}, id="tmp-posix-path"),  # noqa: S108
        pytest.param({"detail": "/srv/runner/proof.json"}, id="generic-posix-path"),
        pytest.param({"detail": r"C:\Users\operator\proof.json"}, id="windows-drive-path"),
        pytest.param({"detail": r"\\server\share\proof.json"}, id="windows-unc-path"),
        pytest.param({"detail": r"\Users\operator\proof.json"}, id="windows-rooted-path"),
        pytest.param({"detail": "${HOME}/proof.json"}, id="embedded-posix-env-reference"),
        pytest.param({"detail": r"%USERPROFILE%\proof.json"}, id="embedded-windows-env-reference"),
        pytest.param({"host-name": "build-host"}, id="hostname-key"),
        pytest.param({"User.Name": "operator"}, id="username-key"),
        pytest.param({"machine-id": "host-123"}, id="machine-id-key"),
        pytest.param({"COMPUTERNAME": "build-host"}, id="computername-env-key"),
        pytest.param({"API-KEY": "credential"}, id="credential-key"),
        pytest.param({"APIKey": "credential"}, id="acronym-credential-key"),
        pytest.param({"AWS_ACCESS_KEY_ID": "credential"}, id="aws-access-key-env-key"),
        pytest.param({"SERVICE_TOKEN": "credential"}, id="credential-env-key"),
        pytest.param({"ALBU_MCP_ALLOWED_ROOT": "relative"}, id="albu-env-key"),
        pytest.param({"HOME": "relative"}, id="machine-env-key"),
    ],
)
def test_evidence_privacy_rejects_structural_machine_data(private_value: object) -> None:
    with pytest.raises(AssertionError):
        _assert_evidence_privacy_safe(private_value)


@pytest.mark.parametrize(
    "safe_value",
    [
        {"token_count": 0},
        {"secret_count": 0},
        {"authorization_mode": "none"},
        {"machine_id_matches": True},
        {"hostname_count": 0},
        {"api_key_count": 0},
    ],
)
def test_evidence_privacy_accepts_harmless_schema_like_words(safe_value: object) -> None:
    _assert_evidence_privacy_safe(safe_value)


def _assert_status_links_published_upgrade_evidence(status: str) -> None:
    digest = hashlib.sha256(_EVIDENCE.read_bytes()).hexdigest()
    expected = (
        "## Protocol Compatibility Evidence\n\n"
        "Status: `passed`\n\n"
        "Status basis: Published upgrade probe result only; this does not assert provenance.\n\n"
        "Published upgrade: `1.20.0 -> 1.21.0`\n\n"
        "Evidence: [privacy-safe machine report]"
        "(host-evidence/published-upgrade-1.20.0-to-1.21.0-2026-08-04.json)\n\n"
        f"Evidence SHA-256: `{digest}`\n\n"
        "Provenance: Local operator-run snapshot. No immutable public run or attestation is available; "
        "this evidence is not independently attested or provenance-verifiable.\n\n"
        "Scope: Streamable HTTP conformance and published-package artifact continuity. "
        "This is not real-host UI evidence.\n"
    )
    start = status.index("## Protocol Compatibility Evidence")
    end = status.index("\n## Host Evidence", start)

    assert status[start:end] == expected


def test_status_links_the_published_upgrade_evidence_with_machine_only_scope() -> None:
    status = _STATUS.read_text(encoding="utf-8")

    _assert_status_links_published_upgrade_evidence(status)


@pytest.mark.parametrize(
    ("current", "replacement"),
    [
        ("Status: `passed`", "Status: `failed`"),
        ("Published upgrade: `1.20.0 -> 1.21.0`", "Published upgrade: `1.19.0 -> 1.21.0`"),
    ],
)
def test_status_rejects_protocol_evidence_section_mutations(current: str, replacement: str) -> None:
    status = _STATUS.read_text(encoding="utf-8")
    mutated = status.replace(current, replacement, 1)
    assert mutated != status

    with pytest.raises(AssertionError):
        _assert_status_links_published_upgrade_evidence(mutated)
