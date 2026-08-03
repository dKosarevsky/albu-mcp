from __future__ import annotations

import argparse
import asyncio
import base64
import copy
import json
import os
import signal
import stat
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest
from mcp.types.version import LATEST_HANDSHAKE_VERSION, LATEST_MODERN_VERSION
from typing_extensions import Self

from albumentationsx_mcp.upgrade_proof import (
    ArtifactContinuity,
    ProtocolObservation,
    PublicSurface,
    UpgradeProofReport,
    build_upgrade_proof_report,
)
from scripts import check_published_package_smoke, check_published_upgrade
from scripts.published_upgrade_runtime import (
    PACKAGE,
    PublishedUpgradeRuntimeError,
    RuntimeCode,
    RuntimePhase,
    StderrCategory,
    build_attested_uvx_server_command,
)

if sys.version_info >= (3, 11):
    from builtins import BaseExceptionGroup as RuntimeBaseExceptionGroup
    from builtins import ExceptionGroup as RuntimeExceptionGroup
else:
    from exceptiongroup import BaseExceptionGroup as RuntimeBaseExceptionGroup  # ty: ignore[unresolved-import]
    from exceptiongroup import ExceptionGroup as RuntimeExceptionGroup  # ty: ignore[unresolved-import]


def _upgrade_report(*, compatible: bool = True) -> UpgradeProofReport:
    old_surface = PublicSurface.build(
        tools=["render_preview_batch"],
        resources=[],
        resource_templates=[],
        prompts=[],
    )
    new_surface = (
        old_surface
        if compatible
        else PublicSurface.build(
            tools=[],
            resources=[],
            resource_templates=[],
            prompts=[],
        )
    )

    def observation(
        version: str,
        mode: str,
        protocol: str,
        surface: PublicSurface,
    ) -> ProtocolObservation:
        return ProtocolObservation(
            server_version=version,
            observed_server_version=version,
            advertised_server_version=version,
            client_mode=mode,
            expected_protocol=protocol,
            negotiated_protocol=protocol,
            surface=surface,
        )

    return build_upgrade_proof_report(
        package=PACKAGE,
        from_version="1.20.0",
        to_version="1.21.0",
        observed_on="2026-08-03",
        from_legacy=observation("1.20.0", "legacy", LATEST_HANDSHAKE_VERSION, old_surface),
        to_legacy=observation("1.21.0", "legacy", LATEST_HANDSHAKE_VERSION, new_surface),
        to_modern=observation("1.21.0", LATEST_MODERN_VERSION, LATEST_MODERN_VERSION, new_surface),
        artifact=ArtifactContinuity(
            manifest_readable=True,
            manifest_run_id_matches=True,
            contact_sheet_readable=True,
            content_unchanged=True,
            contact_sheet_sha256="a" * 64,
        ),
    )


def _install_successful_probe(
    monkeypatch: pytest.MonkeyPatch,
    report: UpgradeProofReport | None = None,
) -> UpgradeProofReport:
    expected = _upgrade_report() if report is None else report

    def fake_probe(
        request: check_published_upgrade._ProbeRequest,
        _timeout_seconds: float,
    ) -> UpgradeProofReport:
        assert request.from_version == "1.20.0"
        assert request.to_version == "1.21.0"
        return expected

    monkeypatch.setattr(check_published_upgrade, "_run_probe", fake_probe)
    monkeypatch.setattr(
        check_published_upgrade,
        "check_pypi_version",
        lambda **_kwargs: _pypi_result("AVAILABLE"),
    )
    return expected


def _pypi_result(state: str) -> object:
    state_value = getattr(check_published_package_smoke.PyPIVersionState, state)
    return check_published_package_smoke.PyPIVersionResult(state=state_value)


def _probe_request() -> check_published_upgrade._ProbeRequest:
    return check_published_upgrade._ProbeRequest(
        from_version="1.20.0",
        to_version="1.21.0",
        observed_on="2026-08-03",
        read_timeout_seconds=20.0,
    )


def _local_child_launcher(
    *,
    payload: bytes = b"",
    repeated_bytes: int | None = None,
    exit_code: int = 0,
) -> Callable[[object], subprocess.Popen[bytes]]:
    if repeated_bytes is None:
        encoded = base64.b64encode(payload).decode("ascii")
        code = f"import base64,sys;sys.stdout.buffer.write(base64.b64decode({encoded!r}));raise SystemExit({exit_code})"
    else:
        code = f"import sys;sys.stdout.buffer.write(b'x'*{repeated_bytes});raise SystemExit({exit_code})"

    def launch(_request: object) -> subprocess.Popen[bytes]:
        return subprocess.Popen(  # noqa: S603 - fixed local interpreter test child.
            [sys.executable, "-c", code],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            start_new_session=os.name == "posix",
            creationflags=(getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0),
        )

    return launch


@pytest.mark.parametrize(
    "version",
    [
        "",
        "latest",
        "1.21",
        "01.21.0",
        "1.021.0",
        "1.21.00",
        "1.21.0rc1",
        "1.21.0;echo",
        "../1.21.0",
        "1.21.0+local",
        "1.21.0/next",
        "1" * 129,
    ],
)
def test_validate_exact_version_rejects_non_release_values(version: str) -> None:
    with pytest.raises(ValueError, match="exact release version"):
        check_published_upgrade.validate_exact_version(version)


@pytest.mark.parametrize("version", ["0.0.0", "1.21.0", "10.200.300"])
def test_validate_exact_version_accepts_three_part_public_releases(version: str) -> None:
    assert check_published_upgrade.validate_exact_version(version) == version


@pytest.mark.parametrize(
    ("from_version", "to_version"),
    [("1.20.0", "1.20.0"), ("1.21.0", "1.20.0"), ("2.0.0", "1.99.99")],
)
def test_version_order_is_rejected_before_external_calls(
    from_version: str,
    to_version: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    external_calls = 0

    def unexpected_call(*_args: object, **_kwargs: object) -> None:
        nonlocal external_calls
        external_calls += 1
        raise AssertionError

    monkeypatch.setattr(check_published_upgrade, "check_pypi_version", unexpected_call)
    monkeypatch.setattr(check_published_upgrade, "_run_probe", unexpected_call)

    with pytest.raises(SystemExit) as caught:
        check_published_upgrade.main(["--from-version", from_version, "--to-version", to_version])

    assert caught.value.code == 2
    assert external_calls == 0
    assert "strictly newer" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("option", "value"),
    [
        ("--retries", "0"),
        ("--retries", "-1"),
        ("--retries", "1000000000"),
        ("--retry-delay", "-0.1"),
        ("--retry-delay", "nan"),
        ("--retry-delay", "inf"),
        ("--retry-delay", "1000000000"),
        ("--pypi-timeout", "0"),
        ("--pypi-timeout", "-1"),
        ("--pypi-timeout", "nan"),
        ("--pypi-timeout", "inf"),
        ("--pypi-timeout", "1000000000"),
        ("--read-timeout", "0"),
        ("--read-timeout", "-1"),
        ("--read-timeout", "nan"),
        ("--read-timeout", "inf"),
        ("--read-timeout", "1000000000"),
        ("--probe-timeout", "0"),
        ("--probe-timeout", "-1"),
        ("--probe-timeout", "nan"),
        ("--probe-timeout", "inf"),
        ("--probe-timeout", "1000000000"),
    ],
)
def test_invalid_numeric_options_are_rejected_before_external_calls(
    option: str,
    value: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    external_calls = 0

    def unexpected_call(*_args: object, **_kwargs: object) -> None:
        nonlocal external_calls
        external_calls += 1
        raise AssertionError

    monkeypatch.setattr(check_published_upgrade, "check_pypi_version", unexpected_call)
    monkeypatch.setattr(check_published_upgrade, "_run_probe", unexpected_call)

    with pytest.raises(SystemExit) as caught:
        check_published_upgrade.main(["--from-version", "1.20.0", "--to-version", "1.21.0", option, value])

    assert caught.value.code == 2
    assert external_calls == 0


def test_observed_on_requires_exact_lexical_iso_date_before_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    class PermissiveDate:
        @classmethod
        def fromisoformat(cls, _value: str) -> object:
            return object()

    monkeypatch.setattr(check_published_upgrade, "date", PermissiveDate)

    with pytest.raises(argparse.ArgumentTypeError, match="YYYY-MM-DD"):
        check_published_upgrade._parse_observed_on("2026-8-3")


def test_dry_run_prints_three_attested_pinned_commands_without_external_calls(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def unexpected_call(*_args: object, **_kwargs: object) -> None:
        raise AssertionError

    monkeypatch.setattr(check_published_upgrade, "check_pypi_version", unexpected_call)
    monkeypatch.setattr(check_published_upgrade, "_run_probe", unexpected_call)
    monkeypatch.setattr(check_published_upgrade.time, "sleep", unexpected_call)

    result = check_published_upgrade.main(["--from-version", "1.20.0", "--to-version", "1.21.0", "--dry-run"])
    payload = json.loads(capsys.readouterr().out)

    assert result == 0
    assert [(item["server_version"], item["client_mode"]) for item in payload["commands"]] == [
        ("1.20.0", "legacy"),
        ("1.21.0", "legacy"),
        ("1.21.0", LATEST_MODERN_VERSION),
    ]
    assert [item["command"] for item in payload["commands"]] == [
        build_attested_uvx_server_command("1.20.0"),
        build_attested_uvx_server_command("1.21.0"),
        build_attested_uvx_server_command("1.21.0"),
    ]
    assert all("--isolated" in item["command"] for item in payload["commands"])


def test_pypi_check_returns_stable_safe_error_for_transport_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sensitive_detail = "https://token@proxy.invalid/private/path"

    def fail_request(*_args: object, **_kwargs: object) -> None:
        raise OSError(sensitive_detail)

    monkeypatch.setattr(check_published_package_smoke.urllib.request, "urlopen", fail_request)

    result = check_published_upgrade.check_pypi_version(
        package=PACKAGE,
        version="1.21.0",
        timeout_seconds=1.0,
    )

    assert result.state is check_published_package_smoke.PyPIVersionState.RETRYABLE_UNAVAILABLE
    assert result.message == "PyPI version endpoint is not visible yet."
    assert sensitive_detail not in result.message


def test_pypi_check_does_not_echo_arbitrary_response_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sensitive_detail = "private-returned-version-token"

    class Response:
        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self, _maximum_bytes: int) -> bytes:
            return json.dumps({"info": {"version": sensitive_detail}}).encode()

    monkeypatch.setattr(check_published_package_smoke.urllib.request, "urlopen", lambda *_args, **_kwargs: Response())

    result = check_published_upgrade.check_pypi_version(
        package=PACKAGE,
        version="1.21.0",
        timeout_seconds=1.0,
    )

    assert result.state is check_published_package_smoke.PyPIVersionState.TERMINAL_VERSION_MISMATCH
    assert result.message == "PyPI version endpoint did not confirm the requested exact version."
    assert sensitive_detail not in result.message


@pytest.mark.parametrize("body", [b"not-json", b"[]", b'{"info": []}'])
def test_pypi_check_classifies_malformed_body_as_terminal(
    body: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Response:
        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self, _maximum_bytes: int) -> bytes:
            return body

    monkeypatch.setattr(check_published_package_smoke.urllib.request, "urlopen", lambda *_args, **_kwargs: Response())

    result = check_published_upgrade.check_pypi_version(
        package=PACKAGE,
        version="1.21.0",
        timeout_seconds=1.0,
    )

    assert result.state is check_published_package_smoke.PyPIVersionState.TERMINAL_MALFORMED
    assert result.retryable is False
    assert result.message == "PyPI version endpoint returned a malformed response."


def test_pypi_check_bounds_response_body_and_rejects_overflow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requested_sizes: list[int] = []

    class Response:
        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self, maximum_bytes: int) -> bytes:
            requested_sizes.append(maximum_bytes)
            return b"x" * maximum_bytes

    monkeypatch.setattr(check_published_package_smoke.urllib.request, "urlopen", lambda *_args, **_kwargs: Response())

    result = check_published_upgrade.check_pypi_version(
        package=PACKAGE,
        version="1.21.0",
        timeout_seconds=1.0,
    )

    assert requested_sizes == [check_published_package_smoke.MAX_PYPI_RESPONSE_BYTES + 1]
    assert result.state is check_published_package_smoke.PyPIVersionState.TERMINAL_MALFORMED


def test_pypi_check_accepts_exact_bounded_version_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Response:
        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self, maximum_bytes: int) -> bytes:
            payload = b'{"info":{"version":"1.21.0"}}'
            assert len(payload) <= maximum_bytes
            return payload

    monkeypatch.setattr(check_published_package_smoke.urllib.request, "urlopen", lambda *_args, **_kwargs: Response())

    result = check_published_upgrade.check_pypi_version(
        package=PACKAGE,
        version="1.21.0",
        timeout_seconds=1.0,
    )

    assert result.state is check_published_package_smoke.PyPIVersionState.AVAILABLE
    assert result.available is True
    assert result.message == ""


def test_pypi_versions_are_retried_deterministically_without_final_sleep(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    attempts: dict[str, int] = {}
    calls: list[str] = []
    sleeps: list[float] = []
    probe_calls = 0

    def fake_check(*, package: str, version: str, timeout_seconds: float) -> object:
        assert package == PACKAGE
        assert timeout_seconds == 2.0
        calls.append(version)
        attempts[version] = attempts.get(version, 0) + 1
        if version == "1.20.0" and attempts[version] >= 2:
            return _pypi_result("AVAILABLE")
        return _pypi_result("RETRYABLE_UNAVAILABLE")

    def unexpected_probe(_request: object, _timeout_seconds: float) -> UpgradeProofReport:
        nonlocal probe_calls
        probe_calls += 1
        raise AssertionError

    monkeypatch.setattr(check_published_upgrade, "check_pypi_version", fake_check)
    monkeypatch.setattr(check_published_upgrade, "_run_probe", unexpected_probe)
    monkeypatch.setattr(check_published_upgrade.time, "sleep", sleeps.append)

    result = check_published_upgrade.main(
        [
            "--from-version",
            "1.20.0",
            "--to-version",
            "1.21.0",
            "--retries",
            "3",
            "--retry-delay",
            "0.25",
            "--pypi-timeout",
            "2",
        ]
    )
    failure = json.loads(capsys.readouterr().err)

    assert result == 1
    assert calls == ["1.20.0", "1.20.0", "1.21.0", "1.21.0", "1.21.0"]
    assert sleeps == [0.25, 0.25, 0.25]
    assert probe_calls == 0
    assert failure["failures"] == [
        {
            "code": "pypi_version_unavailable",
            "remediation": "Retry after the exact release is visible on the public PyPI version endpoint.",
            "scope": "to_version",
        }
    ]


@pytest.mark.parametrize(
    ("terminal_state", "failure_code"),
    [
        ("TERMINAL_VERSION_MISMATCH", "pypi_version_mismatch"),
        ("TERMINAL_MALFORMED", "pypi_response_invalid"),
    ],
)
def test_terminal_pypi_result_fails_immediately_without_retry_or_probe(
    terminal_state: str,
    failure_code: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls = 0
    sleeps: list[float] = []

    def terminal_then_success(**_kwargs: object) -> object:
        nonlocal calls
        calls += 1
        return _pypi_result(terminal_state if calls == 1 else "AVAILABLE")

    def unexpected_probe(*_args: object, **_kwargs: object) -> None:
        raise AssertionError

    monkeypatch.setattr(check_published_upgrade, "check_pypi_version", terminal_then_success)
    monkeypatch.setattr(check_published_upgrade, "_run_probe", unexpected_probe)
    monkeypatch.setattr(check_published_upgrade.time, "sleep", sleeps.append)

    result = check_published_upgrade.main(["--from-version", "1.20.0", "--to-version", "1.21.0", "--retries", "3"])
    failure = json.loads(capsys.readouterr().err)

    assert result == 1
    assert calls == 1
    assert sleeps == []
    assert failure["failures"][0]["code"] == failure_code


def test_smoke_retries_transient_pypi_result_then_runs_command(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    states = iter([_pypi_result("RETRYABLE_UNAVAILABLE"), _pypi_result("AVAILABLE")])
    sleeps: list[float] = []
    command = ["uvx", "package"]
    monkeypatch.setattr(check_published_package_smoke, "check_pypi_version", lambda **_kwargs: next(states))
    monkeypatch.setattr(check_published_package_smoke.time, "sleep", sleeps.append)
    monkeypatch.setattr(
        check_published_package_smoke.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(command, 0, stdout="smoke ok\n", stderr=""),
    )

    check_published_package_smoke.run_smoke(
        check_published_package_smoke.SmokeConfig(
            command=command,
            package=PACKAGE,
            version="1.21.0",
            retries=3,
            delay_seconds=0.25,
        )
    )

    captured = capsys.readouterr()
    assert sleeps == [0.25]
    assert "retrying smoke attempt 1/3" in captured.err
    assert captured.out == "smoke ok\n"


def test_smoke_terminal_pypi_result_does_not_retry_or_run_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def terminal_then_success(**_kwargs: object) -> object:
        nonlocal calls
        calls += 1
        return _pypi_result("TERMINAL_VERSION_MISMATCH" if calls == 1 else "AVAILABLE")

    def unexpected(*_args: object, **_kwargs: object) -> None:
        raise AssertionError

    monkeypatch.setattr(check_published_package_smoke, "check_pypi_version", terminal_then_success)
    monkeypatch.setattr(check_published_package_smoke.time, "sleep", unexpected)
    monkeypatch.setattr(check_published_package_smoke.subprocess, "run", unexpected)

    with pytest.raises(SystemExit) as caught:
        check_published_package_smoke.run_smoke(
            check_published_package_smoke.SmokeConfig(
                command=["uvx", "package"],
                package=PACKAGE,
                version="1.21.0",
                retries=3,
            )
        )

    assert caught.value.code == 1
    assert calls == 1


def test_success_is_printed_as_deterministic_json(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    report = _install_successful_probe(monkeypatch)

    result = check_published_upgrade.main(
        [
            "--from-version",
            "1.20.0",
            "--to-version",
            "1.21.0",
            "--observed-on",
            "2026-08-03",
        ]
    )

    assert result == 0
    assert capsys.readouterr().out == json.dumps(report, indent=2, sort_keys=True) + "\n"


def test_success_writes_report_atomically_after_fsync(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = _install_successful_probe(monkeypatch)
    output = tmp_path / "evidence" / "upgrade.json"
    events: list[str] = []
    original_replace = os.replace

    def fake_fsync(file_descriptor: int) -> None:
        descriptor_kind = "dir_fsync" if stat.S_ISDIR(os.fstat(file_descriptor).st_mode) else "file_fsync"
        events.append(descriptor_kind)

    def recording_replace(
        source: str | os.PathLike[str],
        target: str | os.PathLike[str],
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
    ) -> None:
        events.append("replace")
        original_replace(source, target, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)

    monkeypatch.setattr(check_published_upgrade.os, "fsync", fake_fsync)
    monkeypatch.setattr(check_published_upgrade.os, "replace", recording_replace)

    result = check_published_upgrade.main(
        [
            "--from-version",
            "1.20.0",
            "--to-version",
            "1.21.0",
            "--observed-on",
            "2026-08-03",
            "--output",
            str(output),
        ]
    )

    assert result == 0
    assert output.read_text(encoding="utf-8") == json.dumps(report, indent=2, sort_keys=True) + "\n"
    assert "file_fsync" in events
    assert events.index("file_fsync") < events.index("replace")
    assert events[-1] == "dir_fsync"
    assert list(output.parent.iterdir()) == [output]


def test_failed_report_is_printed_but_preexisting_output_is_preserved(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    report = _upgrade_report(compatible=False)
    _install_successful_probe(monkeypatch, report)
    output = tmp_path / "upgrade.json"
    output.write_text("previous evidence\n", encoding="utf-8")

    result = check_published_upgrade.main(
        [
            "--from-version",
            "1.20.0",
            "--to-version",
            "1.21.0",
            "--observed-on",
            "2026-08-03",
            "--output",
            str(output),
        ]
    )

    assert result == 1
    assert output.read_text(encoding="utf-8") == "previous evidence\n"
    failure = json.loads(capsys.readouterr().err)
    assert failure == report
    assert failure["failures"][0]["code"] == "surface_removed"


@pytest.mark.parametrize(
    "case",
    [
        "partial_pass",
        "context_mismatch",
        "false_row_boolean",
        "failed_artifact_with_pass",
        "nonempty_failures_on_pass",
        "sensitive_unknown_field",
        "malformed_fail",
        "unknown_nested_key",
        "oversized_failures",
    ],
)
def test_cli_rejects_unvalidated_probe_reports_without_echoing_them(
    case: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    sensitive_detail = "https://token@proxy.invalid/private/path"
    report: object
    if case == "partial_pass":
        report = {"status": "pass"}
    else:
        candidate = copy.deepcopy(_upgrade_report())
        if case == "context_mismatch":
            candidate["to_version"] = "1.22.0"
        elif case == "false_row_boolean":
            candidate["matrix"][0]["ok"] = False
        elif case == "failed_artifact_with_pass":
            candidate["artifact_continuity"]["content_unchanged"] = False
        elif case == "nonempty_failures_on_pass":
            failed = _upgrade_report(compatible=False)
            candidate["failures"] = copy.deepcopy(failed["failures"])
        elif case == "sensitive_unknown_field":
            cast("dict[str, object]", candidate)[sensitive_detail] = sensitive_detail
        elif case == "malformed_fail":
            candidate = copy.deepcopy(_upgrade_report(compatible=False))
            candidate["failures"][0]["remediation"] = sensitive_detail
        elif case == "unknown_nested_key":
            cast("dict[str, object]", candidate["matrix"][0])[sensitive_detail] = sensitive_detail
        else:
            failed = _upgrade_report(compatible=False)
            candidate["status"] = "fail"
            candidate["failures"] = copy.deepcopy(failed["failures"] * 65)
        report = candidate

    def fake_probe(_request: object, _timeout_seconds: float) -> object:
        return report

    monkeypatch.setattr(check_published_upgrade, "_run_probe", fake_probe)
    monkeypatch.setattr(
        check_published_upgrade,
        "check_pypi_version",
        lambda **_kwargs: _pypi_result("AVAILABLE"),
    )

    result = check_published_upgrade.main(
        [
            "--from-version",
            "1.20.0",
            "--to-version",
            "1.21.0",
            "--observed-on",
            "2026-08-03",
        ]
    )
    captured = capsys.readouterr()
    failure = json.loads(captured.err)

    assert result == 1
    assert captured.out == ""
    assert failure["failures"] == [
        {
            "code": "probe_execution_failed",
            "reason": "invalid_report",
            "remediation": "Retry with a runtime that emits the current upgrade proof schema.",
        }
    ]
    assert sensitive_detail not in captured.err


def test_probe_timeout_fails_closed_without_replacing_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def blocked_probe(_request: object, _timeout_seconds: float) -> UpgradeProofReport:
        raise check_published_upgrade._ProbeExecutorError(check_published_upgrade._child_failure("timeout"))

    monkeypatch.setattr(check_published_upgrade, "_run_probe", blocked_probe)
    monkeypatch.setattr(
        check_published_upgrade,
        "check_pypi_version",
        lambda **_kwargs: _pypi_result("AVAILABLE"),
    )
    output = tmp_path / "upgrade.json"
    output.write_text("previous evidence\n", encoding="utf-8")

    result = check_published_upgrade.main(
        [
            "--from-version",
            "1.20.0",
            "--to-version",
            "1.21.0",
            "--probe-timeout",
            "0.001",
            "--output",
            str(output),
        ]
    )
    failure = json.loads(capsys.readouterr().err)

    assert result == 1
    assert output.read_text(encoding="utf-8") == "previous evidence\n"
    assert failure["failures"][0]["code"] == "probe_execution_failed"
    assert failure["failures"][0]["reason"] == "timeout"


def test_probe_executor_accepts_bounded_canonical_child_report() -> None:
    report = _upgrade_report()
    payload = json.dumps(
        {"kind": "report", "report": report},
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()

    observed = check_published_upgrade._run_probe(
        _probe_request(),
        2.0,
        launcher=_local_child_launcher(payload=payload),
    )

    assert observed == report


def test_probe_executor_converts_structured_runtime_child_error() -> None:
    payload = json.dumps(
        {
            "kind": "runtime_error",
            "phase": "negotiation",
            "code": "negotiation_failed",
            "diagnostic": "other",
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode()

    with pytest.raises(check_published_upgrade._ProbeExecutorError) as caught:
        check_published_upgrade._run_probe(
            _probe_request(),
            2.0,
            launcher=_local_child_launcher(payload=payload),
        )

    assert caught.value.failure == {
        "code": "probe_execution_failed",
        "diagnostic": "other",
        "phase": "negotiation",
        "remediation": "Retry after checking PyPI visibility and published server diagnostics locally.",
        "runtime_code": "negotiation_failed",
    }


def test_operator_preserves_finite_probe_executor_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    failure = {
        "code": "probe_execution_failed",
        "reason": "child_process_failed",
        "remediation": "Retry after checking the local Python runtime and published probe environment.",
    }

    def failed_probe(_request: object, _timeout_seconds: float) -> UpgradeProofReport:
        raise check_published_upgrade._ProbeExecutorError(failure)

    monkeypatch.setattr(check_published_upgrade, "_run_probe", failed_probe)
    monkeypatch.setattr(
        check_published_upgrade,
        "check_pypi_version",
        lambda **_kwargs: _pypi_result("AVAILABLE"),
    )

    result = check_published_upgrade.main(["--from-version", "1.20.0", "--to-version", "1.21.0"])

    assert result == 1
    assert json.loads(capsys.readouterr().err)["failures"] == [failure]


def test_script_entrypoint_routes_private_child_mode_without_argparse_output() -> None:
    script = Path(check_published_upgrade.__file__)
    result = subprocess.run(  # noqa: S603 - fixed local Python child entrypoint.
        [sys.executable, str(script), check_published_upgrade._CHILD_MODE, "invalid-request"],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=False,
        timeout=2.0,
    )

    payload = json.loads(result.stdout)
    assert result.returncode == 0
    assert result.stderr == b""
    assert payload == {"kind": "error", "reason": "child_payload_invalid"}


@pytest.mark.parametrize(
    ("launcher", "reason"),
    [
        (_local_child_launcher(payload=b"private malformed child payload"), "child_payload_invalid"),
        (
            _local_child_launcher(repeated_bytes=check_published_upgrade._MAX_CHILD_PAYLOAD_BYTES + 1),
            "child_payload_invalid",
        ),
        (_local_child_launcher(exit_code=23), "child_process_failed"),
    ],
)
def test_probe_executor_rejects_unsafe_child_results(
    launcher: Callable[[object], subprocess.Popen[bytes]],
    reason: str,
) -> None:
    with pytest.raises(check_published_upgrade._ProbeExecutorError) as caught:
        check_published_upgrade._run_probe(_probe_request(), 2.0, launcher=launcher)

    assert caught.value.failure["reason"] == reason
    assert "private malformed child payload" not in json.dumps(caught.value.failure)


@pytest.mark.skipif(os.name != "posix", reason="POSIX process-group kill assertion")
def test_probe_watchdog_kills_and_reaps_sigterm_resistant_child_within_hard_bound() -> None:
    processes: list[subprocess.Popen[bytes]] = []
    code = (
        "import signal,sys;"
        "signal.signal(signal.SIGTERM, signal.SIG_IGN);"
        "sys.stdout.buffer.write(b'ready');sys.stdout.buffer.flush();"
        "signal.pause()"
    )

    def launch(_request: object) -> subprocess.Popen[bytes]:
        process = subprocess.Popen(  # noqa: S603 - fixed local watchdog test child.
            [sys.executable, "-c", code],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        processes.append(process)
        return process

    started = time.monotonic()
    with pytest.raises(check_published_upgrade._ProbeExecutorError) as caught:
        check_published_upgrade._run_probe(_probe_request(), 0.2, launcher=launch)
    elapsed = time.monotonic() - started

    assert caught.value.failure["reason"] == "timeout"
    assert elapsed < 2.0
    assert len(processes) == 1
    assert processes[0].poll() is not None
    assert processes[0].returncode == -signal.SIGKILL


def test_python_310_asyncio_timeout_is_classified_once_through_exception_group(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class SimulatedAsyncioTimeoutError(Exception):
        pass

    def failed_probe(_request: object, _timeout_seconds: float) -> UpgradeProofReport:
        message = "private timeout group"
        raise RuntimeExceptionGroup(message, [SimulatedAsyncioTimeoutError("private timeout detail")])

    monkeypatch.setattr(check_published_upgrade.asyncio, "TimeoutError", SimulatedAsyncioTimeoutError)
    monkeypatch.setattr(check_published_upgrade, "_run_probe", failed_probe)
    monkeypatch.setattr(
        check_published_upgrade,
        "check_pypi_version",
        lambda **_kwargs: _pypi_result("AVAILABLE"),
    )

    result = check_published_upgrade.main(["--from-version", "1.20.0", "--to-version", "1.21.0"])
    failure = json.loads(capsys.readouterr().err)

    assert result == 1
    assert failure["failures"] == [
        {
            "code": "probe_execution_failed",
            "reason": "timeout",
            "remediation": "Retry with a bounded probe timeout after checking published server startup locally.",
        }
    ]


def test_runtime_failure_uses_only_finite_safe_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def failed_probe(_request: object, _timeout_seconds: float) -> UpgradeProofReport:
        raise PublishedUpgradeRuntimeError(
            phase=RuntimePhase.NEGOTIATION,
            code=RuntimeCode.NEGOTIATION_FAILED,
            diagnostic=StderrCategory.OTHER,
        )

    monkeypatch.setattr(check_published_upgrade, "_run_probe", failed_probe)
    monkeypatch.setattr(
        check_published_upgrade,
        "check_pypi_version",
        lambda **_kwargs: _pypi_result("AVAILABLE"),
    )

    result = check_published_upgrade.main(["--from-version", "1.20.0", "--to-version", "1.21.0"])
    failure = json.loads(capsys.readouterr().err)

    assert result == 1
    assert failure["failures"][0] == {
        "code": "probe_execution_failed",
        "diagnostic": "other",
        "phase": "negotiation",
        "remediation": "Retry after checking PyPI visibility and published server diagnostics locally.",
        "runtime_code": "negotiation_failed",
    }


@pytest.mark.parametrize("error_type", [OSError, RuntimeError])
def test_pypi_check_normalizes_every_ordinary_operational_exception(
    error_type: type[Exception],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sensitive_detail = "https://token@proxy.invalid/private/path"

    def fail_request(*_args: object, **_kwargs: object) -> None:
        raise error_type(sensitive_detail)

    monkeypatch.setattr(check_published_package_smoke.urllib.request, "urlopen", fail_request)

    result = check_published_upgrade.check_pypi_version(
        package=PACKAGE,
        version="1.21.0",
        timeout_seconds=1.0,
    )

    assert result.state is check_published_package_smoke.PyPIVersionState.RETRYABLE_UNAVAILABLE
    assert result.message == "PyPI version endpoint is not visible yet."
    assert sensitive_detail not in result.message


@pytest.mark.parametrize(
    "error_factory",
    [
        lambda: OSError("https://token@proxy.invalid/private/path"),
        lambda: RuntimeExceptionGroup(
            "private exception group",
            [OSError("https://token@proxy.invalid/private/path")],
        ),
    ],
)
def test_operational_probe_failure_does_not_leak_exception_text(
    error_factory: Callable[[], Exception],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def failed_probe(_request: object, _timeout_seconds: float) -> UpgradeProofReport:
        raise error_factory()

    monkeypatch.setattr(check_published_upgrade, "_run_probe", failed_probe)
    monkeypatch.setattr(
        check_published_upgrade,
        "check_pypi_version",
        lambda **_kwargs: _pypi_result("AVAILABLE"),
    )

    result = check_published_upgrade.main(["--from-version", "1.20.0", "--to-version", "1.21.0"])
    encoded = capsys.readouterr().err
    failure = json.loads(encoded)

    assert result == 1
    assert failure["failures"][0]["reason"] == "operational_error"
    assert "token@proxy.invalid" not in encoded
    assert "/private/path" not in encoded
    assert "private exception group" not in encoded


@pytest.mark.parametrize(
    "error_factory",
    [
        asyncio.CancelledError,
        KeyboardInterrupt,
        lambda: SystemExit(7),
        lambda: RuntimeBaseExceptionGroup("private cancellation", [asyncio.CancelledError()]),
    ],
)
def test_control_flow_exceptions_are_not_swallowed(
    error_factory: Callable[[], BaseException],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = error_factory()

    def interrupted_probe(_request: object, _timeout_seconds: float) -> UpgradeProofReport:
        raise error

    monkeypatch.setattr(check_published_upgrade, "_run_probe", interrupted_probe)
    monkeypatch.setattr(
        check_published_upgrade,
        "check_pypi_version",
        lambda **_kwargs: _pypi_result("AVAILABLE"),
    )

    with pytest.raises((asyncio.CancelledError, KeyboardInterrupt, SystemExit)) as caught:
        check_published_upgrade.main(["--from-version", "1.20.0", "--to-version", "1.21.0"])

    assert caught.value.__suppress_context__ is True


def test_atomic_write_failure_cleans_temp_and_preserves_existing_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _install_successful_probe(monkeypatch)
    output = tmp_path / "upgrade.json"
    output.write_text("previous evidence\n", encoding="utf-8")
    secret = str(tmp_path / "private-write-token")

    def fail_replace(_source: object, _target: object, **_kwargs: object) -> None:
        raise OSError(secret)

    monkeypatch.setattr(check_published_upgrade.os, "replace", fail_replace)

    result = check_published_upgrade.main(
        [
            "--from-version",
            "1.20.0",
            "--to-version",
            "1.21.0",
            "--observed-on",
            "2026-08-03",
            "--output",
            str(output),
        ]
    )
    encoded = capsys.readouterr().err

    assert result == 1
    assert output.read_text(encoding="utf-8") == "previous evidence\n"
    assert list(tmp_path.iterdir()) == [output]
    assert json.loads(encoded)["failures"][0]["code"] == "output_write_failed"
    assert secret not in encoded


def test_existing_output_symlink_is_rejected_without_touching_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _install_successful_probe(monkeypatch)
    target = tmp_path / "target.json"
    target.write_text("previous evidence\n", encoding="utf-8")
    output = tmp_path / "upgrade.json"
    output.symlink_to(target)

    result = check_published_upgrade.main(
        [
            "--from-version",
            "1.20.0",
            "--to-version",
            "1.21.0",
            "--observed-on",
            "2026-08-03",
            "--output",
            str(output),
        ]
    )

    assert result == 1
    assert output.is_symlink()
    assert target.read_text(encoding="utf-8") == "previous evidence\n"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["target.json", "upgrade.json"]
    assert json.loads(capsys.readouterr().err)["failures"][0]["code"] == "output_write_failed"


def test_output_symlink_ancestor_is_rejected_without_creating_through_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _install_successful_probe(monkeypatch)
    target_directory = tmp_path / "target"
    target_directory.mkdir()
    linked_directory = tmp_path / "linked"
    linked_directory.symlink_to(target_directory, target_is_directory=True)
    output = linked_directory / "evidence" / "upgrade.json"

    result = check_published_upgrade.main(
        [
            "--from-version",
            "1.20.0",
            "--to-version",
            "1.21.0",
            "--observed-on",
            "2026-08-03",
            "--output",
            str(output),
        ]
    )

    assert result == 1
    assert not (target_directory / "evidence").exists()
    assert json.loads(capsys.readouterr().err)["failures"][0]["code"] == "output_write_failed"


@pytest.mark.skipif(os.name != "posix", reason="POSIX dirfd race assertion")
def test_posix_writer_is_anchored_when_parent_path_is_swapped(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = tmp_path / "parent"
    parent.mkdir()
    displaced = tmp_path / "displaced"
    attacker = tmp_path / "attacker"
    attacker.mkdir()
    output = parent / "upgrade.json"
    original_replace = os.replace

    def swap_parent_then_replace(
        source: str | os.PathLike[str],
        target: str | os.PathLike[str],
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
    ) -> None:
        assert src_dir_fd is not None
        assert src_dir_fd == dst_dir_fd
        parent.rename(displaced)
        parent.symlink_to(attacker, target_is_directory=True)
        original_replace(source, target, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)

    monkeypatch.setattr(check_published_upgrade.os, "replace", swap_parent_then_replace)

    check_published_upgrade._write_atomic(output, "proof\n")

    assert (displaced / "upgrade.json").read_text(encoding="utf-8") == "proof\n"
    assert not (attacker / "upgrade.json").exists()


def test_non_posix_fallback_writes_and_rejects_symlink_ancestors(tmp_path: Path) -> None:
    output = tmp_path / "evidence" / "upgrade.json"
    check_published_upgrade._write_atomic_fallback(output, "proof\n")
    assert output.read_text(encoding="utf-8") == "proof\n"

    target_directory = tmp_path / "target"
    target_directory.mkdir()
    linked_directory = tmp_path / "linked"
    linked_directory.symlink_to(target_directory, target_is_directory=True)

    with pytest.raises(OSError, match="non-symlink directory"):
        check_published_upgrade._write_atomic_fallback(linked_directory / "upgrade.json", "other\n")

    assert not (target_directory / "upgrade.json").exists()
