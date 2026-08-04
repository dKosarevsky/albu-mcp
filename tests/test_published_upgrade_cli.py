from __future__ import annotations

import argparse
import asyncio
import base64
import contextlib
import copy
import hashlib
import io
import json
import os
import signal
import stat
import subprocess
import sys
import threading
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
    SurfaceSummary,
    UpgradeProofReport,
    build_upgrade_proof_report,
)
from scripts import check_published_package_smoke, check_published_upgrade, windows_job
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


def _upgrade_report_with_invalid_set_summary(case: str) -> UpgradeProofReport:
    report = copy.deepcopy(_upgrade_report())
    empty_digest = hashlib.sha256(b"[]").hexdigest()
    values = {
        "old_gt_new_zero_missing": (2, "a" * 64, 1, "b" * 64, 0, empty_digest),
        "equal_counts_different_hashes": (1, "a" * 64, 1, "b" * 64, 0, empty_digest),
        "impossible_retained_count": (3, "a" * 64, 1, "b" * 64, 1, "c" * 64),
        "full_missing_digest_mismatch": (2, "a" * 64, 0, empty_digest, 2, "c" * 64),
    }
    old_count, old_hash, new_count, new_hash, missing_count, missing_hash = values[case]
    old_summary: SurfaceSummary = {"count": old_count, "sha256": old_hash}
    new_summary: SurfaceSummary = {"count": new_count, "sha256": new_hash}
    report["matrix"][0]["surface"]["tools"] = copy.deepcopy(old_summary)
    report["matrix"][1]["surface"]["tools"] = copy.deepcopy(new_summary)
    report["matrix"][2]["surface"]["tools"] = copy.deepcopy(new_summary)
    category = report["compatibility"]["categories"]["tools"]
    category["old"] = old_summary
    category["new"] = new_summary
    category["missing_count"] = missing_count
    category["missing_sha256"] = missing_hash
    category["ok"] = missing_count == 0
    if missing_count:
        report["compatibility"]["old_surface_is_subset"] = False
        report["status"] = "fail"
        report["failures"] = [
            {
                "code": "surface_removed",
                "scope": "tools",
                "missing_count": missing_count,
                "missing_sha256": missing_hash,
                "remediation": "Restore the published identifier or document and version a breaking change.",
            }
        ]
    return report


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
) -> Callable[[object], check_published_upgrade._ManagedProbe]:
    if repeated_bytes is None:
        encoded = base64.b64encode(payload).decode("ascii")
        code = f"import base64,sys;sys.stdout.buffer.write(base64.b64decode({encoded!r}));raise SystemExit({exit_code})"
    else:
        code = f"import sys;sys.stdout.buffer.write(b'x'*{repeated_bytes});raise SystemExit({exit_code})"

    def launch(_request: object) -> check_published_upgrade._ManagedProbe:
        process = subprocess.Popen(  # noqa: S603 - fixed local interpreter test child.
            [sys.executable, "-c", code],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            start_new_session=os.name == "posix",
            creationflags=(getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0),
        )
        return check_published_upgrade._ManagedProbe(
            process=process,
            process_group=process.pid if os.name == "posix" else None,
            owner=check_published_upgrade._NoopProcessTreeOwner(),
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
    output.parent.mkdir()
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


def test_missing_output_parent_fails_without_creating_filesystem(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _install_successful_probe(monkeypatch)
    output = tmp_path / "missing" / "upgrade.json"

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
    assert not output.parent.exists()
    assert list(tmp_path.iterdir()) == []
    assert json.loads(capsys.readouterr().err)["failures"][0]["code"] == "output_write_failed"


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


@pytest.mark.parametrize(
    "case",
    [
        "old_gt_new_zero_missing",
        "equal_counts_different_hashes",
        "impossible_retained_count",
        "full_missing_digest_mismatch",
    ],
)
def test_cli_refuses_to_persist_impossible_set_summary_mathematics(
    case: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    report = _upgrade_report_with_invalid_set_summary(case)

    def fake_probe(_request: object, _timeout_seconds: float) -> object:
        return report

    monkeypatch.setattr(check_published_upgrade, "_run_probe", fake_probe)
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
            "--observed-on",
            "2026-08-03",
            "--output",
            str(output),
        ]
    )

    assert result == 1
    assert output.read_text(encoding="utf-8") == "previous evidence\n"
    assert json.loads(capsys.readouterr().err)["failures"][0]["reason"] == "invalid_report"


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
    launcher: Callable[[object], check_published_upgrade._ManagedProbe],
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

    def launch(_request: object) -> check_published_upgrade._ManagedProbe:
        process = subprocess.Popen(  # noqa: S603 - fixed local watchdog test child.
            [sys.executable, "-c", code],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        processes.append(process)
        return check_published_upgrade._ManagedProbe(
            process=process,
            process_group=process.pid,
            owner=check_published_upgrade._NoopProcessTreeOwner(),
        )

    started = time.monotonic()
    with pytest.raises(check_published_upgrade._ProbeExecutorError) as caught:
        check_published_upgrade._run_probe(_probe_request(), 0.2, launcher=launch)
    elapsed = time.monotonic() - started

    assert caught.value.failure["reason"] == "timeout"
    assert elapsed < 2.0
    assert len(processes) == 1
    assert processes[0].poll() is not None
    assert processes[0].returncode == -signal.SIGKILL


@pytest.mark.skipif(os.name != "posix", reason="POSIX process-group descendant assertion")
def test_probe_watchdog_kills_descendant_after_worker_exits(tmp_path: Path) -> None:
    pid_file = tmp_path / "descendant.pid"
    descendant_code = "import signal;signal.signal(signal.SIGTERM,signal.SIG_IGN);signal.pause()"
    worker_code = (
        "import pathlib,subprocess;"
        f"child=subprocess.Popen([{sys.executable!r},'-c',{descendant_code!r}],"
        "stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);"
        f"pathlib.Path({str(pid_file)!r}).write_text(str(child.pid),encoding='utf-8')"
    )
    processes: list[subprocess.Popen[bytes]] = []

    def launch(_request: object) -> check_published_upgrade._ManagedProbe:
        process = subprocess.Popen(  # noqa: S603 - fixed local process-tree test child.
            [sys.executable, "-c", worker_code],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        process.wait(timeout=1.0)
        processes.append(process)
        return check_published_upgrade._ManagedProbe(
            process=process,
            process_group=process.pid,
            owner=check_published_upgrade._NoopProcessTreeOwner(),
        )

    with pytest.raises(check_published_upgrade._ProbeExecutorError):
        check_published_upgrade._run_probe(_probe_request(), 2.0, launcher=launch)

    descendant_pid = int(pid_file.read_text(encoding="utf-8"))
    deadline = time.monotonic() + 1.0
    while _pid_is_live(descendant_pid) and time.monotonic() < deadline:
        pass
    descendant_live = _pid_is_live(descendant_pid)
    if descendant_live:
        os.kill(descendant_pid, signal.SIGKILL)
    assert processes[0].returncode == 0
    assert not descendant_live


def _pid_is_live(pid: int) -> bool:
    result = subprocess.run(  # noqa: S603 - fixed local process-status command.
        ["ps", "-o", "state=", "-p", str(pid)],  # noqa: S607 - fixed POSIX test utility.
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=False,
        text=True,
    )
    return result.returncode == 0 and not result.stdout.strip().startswith("Z")


def test_windows_tree_kill_uses_fixed_bounded_taskkill(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(check_published_upgrade.subprocess, "run", fake_run)

    assert check_published_upgrade._kill_windows_process_tree(321) is True
    assert calls == [
        (
            ["taskkill", "/PID", "321", "/T", "/F"],
            {
                "stdin": subprocess.DEVNULL,
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
                "check": False,
                "timeout": check_published_upgrade._PROCESS_KILL_GRACE_SECONDS,
            },
        )
    ]


def test_windows_job_owner_configures_assigns_and_closes_idempotently() -> None:
    assert windows_job is not None
    events: list[tuple[str, object]] = []

    class FakeWinApi:
        def create_job(self) -> object:
            events.append(("create", None))
            return 41

        def configure_kill_on_close(self, job_handle: object) -> None:
            events.append(("configure", job_handle))

        def assign_process(self, job_handle: object, process_handle: object) -> None:
            events.append(("assign", (job_handle, process_handle)))

        def terminate_job(self, job_handle: object, exit_code: int) -> None:
            raise AssertionError((job_handle, exit_code))

        def close_handle(self, handle: object) -> None:
            events.append(("close", handle))

    owner = windows_job.WindowsJobOwner.create(api=FakeWinApi())
    owner.assign(321)
    owner.close()
    owner.close()

    assert events == [
        ("create", None),
        ("configure", 41),
        ("assign", (41, 321)),
        ("close", 41),
    ]


def test_windows_job_close_failure_retains_handle_for_terminate_and_retry() -> None:
    assert windows_job is not None
    events: list[tuple[str, object]] = []
    close_attempts = 0
    private_detail = "private native close failure for handle 0x29"

    class FakeWinApi:
        def create_job(self) -> object:
            return 41

        def configure_kill_on_close(self, job_handle: object) -> None:
            assert job_handle == 41

        def assign_process(self, job_handle: object, process_handle: object) -> None:
            raise AssertionError((job_handle, process_handle))

        def terminate_job(self, job_handle: object, exit_code: int) -> None:
            events.append(("terminate", (job_handle, exit_code)))

        def close_handle(self, handle: object) -> None:
            nonlocal close_attempts
            close_attempts += 1
            events.append(("close", handle))
            if close_attempts == 1:
                raise OSError(private_detail)

    owner = windows_job.WindowsJobOwner.create(api=FakeWinApi())

    with pytest.raises(windows_job.WindowsJobError) as caught:
        owner.close()
    owner.terminate()
    owner.close()
    owner.close()

    assert caught.value.__cause__ is None
    assert "private" not in str(caught.value)
    assert events == [
        ("close", 41),
        ("terminate", (41, windows_job._JOB_TERMINATION_EXIT_CODE)),
        ("close", 41),
    ]


def test_windows_job_terminate_failure_is_finite_and_owner_remains_closeable() -> None:
    assert windows_job is not None
    events: list[tuple[str, object]] = []
    private_detail = r"TerminateJobObject failed for C:\private\probe handle 0x29"

    class FakeWinApi:
        def create_job(self) -> object:
            return 41

        def configure_kill_on_close(self, job_handle: object) -> None:
            assert job_handle == 41

        def assign_process(self, job_handle: object, process_handle: object) -> None:
            raise AssertionError((job_handle, process_handle))

        def terminate_job(self, job_handle: object, exit_code: int) -> None:
            events.append(("terminate", (job_handle, exit_code)))
            raise OSError(private_detail)

        def close_handle(self, handle: object) -> None:
            events.append(("close", handle))

    owner = windows_job.WindowsJobOwner.create(api=FakeWinApi())

    with pytest.raises(windows_job.WindowsJobError) as caught:
        owner.terminate()
    owner.close()

    assert caught.value.__cause__ is None
    assert private_detail not in str(caught.value)
    assert events == [
        ("terminate", (41, windows_job._JOB_TERMINATION_EXIT_CODE)),
        ("close", 41),
    ]


@pytest.mark.parametrize(
    ("pointer_size", "actual_sizes"),
    [
        (4, (48, 48, 112)),
        (8, (64, 48, 144)),
    ],
)
def test_windows_job_ctypes_abi_accepts_supported_layouts(
    pointer_size: int,
    actual_sizes: tuple[int, int, int],
) -> None:
    windows_job._validate_job_object_abi(pointer_size=pointer_size, actual_sizes=actual_sizes)


@pytest.mark.parametrize(
    ("pointer_size", "actual_sizes"),
    [
        (2, (48, 48, 112)),
        (4, (44, 48, 108)),
        (8, (64, 48, 136)),
    ],
)
def test_windows_job_ctypes_abi_rejects_unknown_layouts(
    pointer_size: int,
    actual_sizes: tuple[int, int, int],
) -> None:
    with pytest.raises(windows_job.WindowsJobError) as caught:
        windows_job._validate_job_object_abi(pointer_size=pointer_size, actual_sizes=actual_sizes)

    assert caught.value.__cause__ is None
    assert str(caught.value) == "Windows process ownership could not be established."


def test_windows_job_adapter_never_reopens_worker_by_pid() -> None:
    source = Path(windows_job.__file__).read_text(encoding="utf-8")

    assert "AssignProcessToJobObject" in source
    assert "OpenProcess" not in source


def test_windows_job_configuration_failure_closes_handle_and_discards_details() -> None:
    assert windows_job is not None
    events: list[tuple[str, object]] = []
    private_detail = r"CreateJobObjectW failed for C:\private\probe with handle 0x1234"

    class FakeWinApi:
        def create_job(self) -> object:
            return 41

        def configure_kill_on_close(self, job_handle: object) -> None:
            events.append(("configure", job_handle))
            raise OSError(private_detail)

        def assign_process(self, job_handle: object, process_handle: object) -> None:
            raise AssertionError((job_handle, process_handle))

        def terminate_job(self, job_handle: object, exit_code: int) -> None:
            raise AssertionError((job_handle, exit_code))

        def close_handle(self, handle: object) -> None:
            events.append(("close", handle))

    with pytest.raises(windows_job.WindowsJobError) as caught:
        windows_job.WindowsJobOwner.create(api=FakeWinApi())

    assert events == [("configure", 41), ("close", 41)]
    assert caught.value.__cause__ is None
    assert private_detail not in str(caught.value)


def test_windows_job_configuration_control_flow_closes_handle_before_propagation() -> None:
    events: list[tuple[str, object]] = []

    class FakeWinApi:
        def create_job(self) -> object:
            return 41

        def configure_kill_on_close(self, job_handle: object) -> None:
            events.append(("configure", job_handle))
            raise KeyboardInterrupt

        def assign_process(self, job_handle: object, process_handle: object) -> None:
            raise AssertionError((job_handle, process_handle))

        def terminate_job(self, job_handle: object, exit_code: int) -> None:
            raise AssertionError((job_handle, exit_code))

        def close_handle(self, handle: object) -> None:
            events.append(("close", handle))

    with pytest.raises(KeyboardInterrupt):
        windows_job.WindowsJobOwner.create(api=FakeWinApi())

    assert events == [("configure", 41), ("close", 41)]


def test_windows_job_creation_failure_discards_details() -> None:
    assert windows_job is not None
    private_detail = r"CreateJobObjectW failed for C:\private\probe with handle 0x1234"

    class FakeWinApi:
        def create_job(self) -> object:
            raise OSError(private_detail)

        def configure_kill_on_close(self, job_handle: object) -> None:
            raise AssertionError(job_handle)

        def assign_process(self, job_handle: object, process_handle: object) -> None:
            raise AssertionError((job_handle, process_handle))

        def terminate_job(self, job_handle: object, exit_code: int) -> None:
            raise AssertionError((job_handle, exit_code))

        def close_handle(self, handle: object) -> None:
            raise AssertionError(handle)

    with pytest.raises(windows_job.WindowsJobError) as caught:
        windows_job.WindowsJobOwner.create(api=FakeWinApi())

    assert caught.value.__cause__ is None
    assert private_detail not in str(caught.value)


def test_windows_job_assignment_failure_is_finite_and_owner_remains_closeable() -> None:
    assert windows_job is not None
    events: list[tuple[str, object]] = []
    private_detail = "AssignProcessToJobObject failed for handle 0x1234"

    class FakeWinApi:
        def create_job(self) -> object:
            return 41

        def configure_kill_on_close(self, job_handle: object) -> None:
            del job_handle

        def assign_process(self, job_handle: object, process_handle: object) -> None:
            events.append(("assign", (job_handle, process_handle)))
            raise OSError(private_detail)

        def terminate_job(self, job_handle: object, exit_code: int) -> None:
            raise AssertionError((job_handle, exit_code))

        def close_handle(self, handle: object) -> None:
            events.append(("close", handle))

    owner = windows_job.WindowsJobOwner.create(api=FakeWinApi())
    with pytest.raises(windows_job.WindowsJobError) as caught:
        owner.assign(321)
    owner.close()

    assert events == [("assign", (41, 321)), ("close", 41)]
    assert caught.value.__cause__ is None
    assert private_detail not in str(caught.value)


@pytest.mark.skipif(os.name == "nt", reason="non-Windows adapter guard assertion")
def test_windows_job_native_factory_is_importable_and_fails_closed_on_posix() -> None:
    assert windows_job is not None

    with pytest.raises(windows_job.WindowsJobError) as caught:
        windows_job.create_windows_job_owner()

    assert caught.value.__cause__ is None
    assert str(caught.value) == "Windows process ownership is unavailable."


def test_windows_job_native_adapter_load_failure_is_finite(monkeypatch: pytest.MonkeyPatch) -> None:
    private_detail = r"kernel32 load failed from C:\private\system path"

    def fail_adapter_load() -> None:
        raise OSError(private_detail)

    monkeypatch.setattr(windows_job.os, "name", "nt")
    monkeypatch.setattr(windows_job, "_CtypesWindowsJobApi", fail_adapter_load, raising=False)

    with pytest.raises(windows_job.WindowsJobError) as caught:
        windows_job.create_windows_job_owner()

    assert caught.value.__cause__ is None
    assert private_detail not in str(caught.value)


def test_windows_probe_launch_orders_job_assignment_before_gate_release() -> None:
    assert windows_job is not None
    events: list[str] = []

    class FakeWinApi:
        def create_job(self) -> object:
            events.append("create")
            return 41

        def configure_kill_on_close(self, job_handle: object) -> None:
            assert job_handle == 41
            events.append("configure")

        def assign_process(self, job_handle: object, process_handle: object) -> None:
            assert (job_handle, process_handle) == (41, 654)
            events.append("assign")

        def terminate_job(self, job_handle: object, exit_code: int) -> None:
            raise AssertionError((job_handle, exit_code))

        def close_handle(self, handle: object) -> None:
            assert handle == 41
            events.append("job_close")

    class FakeGate:
        def write(self, data: bytes) -> int:
            assert data == check_published_upgrade._WINDOWS_GATE_TOKEN
            events.append("release")
            return len(data)

        def flush(self) -> None:
            events.append("flush")

        def close(self) -> None:
            events.append("gate_close")

    class FakeProcess:
        pid = 321
        _handle = 654
        stdin = FakeGate()
        stdout = None

    def create_owner() -> windows_job.WindowsJobOwner:
        return windows_job.create_windows_job_owner(api=FakeWinApi())

    def popen(command: list[str], **kwargs: object) -> subprocess.Popen[bytes]:
        assert command[2:4] == [check_published_upgrade._CHILD_MODE, check_published_upgrade._WINDOWS_GATE_MODE]
        assert kwargs["stdin"] == subprocess.PIPE
        events.append("launch")
        return cast("subprocess.Popen[bytes]", FakeProcess())

    managed = check_published_upgrade._launch_windows_probe_process(
        _probe_request(),
        owner_factory=create_owner,
        popen=popen,
    )

    assert events == ["create", "configure", "launch", "assign", "release", "flush", "gate_close"]
    managed.close_owner()
    assert events[-1] == "job_close"


@pytest.mark.parametrize("native_handle", [None, 0, -1, True, "654", 1 << 256])
def test_windows_probe_invalid_native_handle_keeps_gate_closed_and_reaps_worker(
    native_handle: object,
) -> None:
    events: list[str] = []

    class FakeWinApi:
        def create_job(self) -> object:
            events.append("create")
            return 41

        def configure_kill_on_close(self, job_handle: object) -> None:
            assert job_handle == 41
            events.append("configure")

        def assign_process(self, job_handle: object, process_handle: object) -> None:
            events.append("assign")
            raise AssertionError((job_handle, process_handle))

        def terminate_job(self, job_handle: object, exit_code: int) -> None:
            assert (job_handle, exit_code) == (41, windows_job._JOB_TERMINATION_EXIT_CODE)
            events.append("job_terminate")

        def close_handle(self, handle: object) -> None:
            assert handle == 41
            events.append("job_close")

    class FakeGate:
        def write(self, _data: bytes) -> int:
            events.append("release")
            return 1

        def flush(self) -> None:
            events.append("flush")

        def close(self) -> None:
            events.append("gate_close")

    class FakeProcess:
        pid = 321
        stdin = FakeGate()
        stdout = io.BytesIO()
        returncode: int | None = None

        def __init__(self) -> None:
            self._handle = native_handle

        def poll(self) -> int | None:
            return self.returncode

        def terminate(self) -> None:
            events.append("worker_stop")
            self.returncode = -15

        def kill(self) -> None:
            events.append("worker_kill")
            self.returncode = -9

        def wait(self, *, timeout: float) -> int:
            assert timeout <= check_published_upgrade._PROCESS_KILL_GRACE_SECONDS
            events.append("worker_reap")
            assert self.returncode is not None
            return self.returncode

    def create_owner() -> windows_job.WindowsJobOwner:
        return windows_job.create_windows_job_owner(api=FakeWinApi())

    def popen(_command: list[str], **_kwargs: object) -> subprocess.Popen[bytes]:
        events.append("launch")
        return cast("subprocess.Popen[bytes]", FakeProcess())

    def launch(request: check_published_upgrade._ProbeRequest) -> check_published_upgrade._ManagedProbe:
        return check_published_upgrade._launch_windows_probe_process(
            request,
            owner_factory=create_owner,
            popen=popen,
        )

    with pytest.raises(check_published_upgrade._ProbeExecutorError) as caught:
        check_published_upgrade._run_probe(_probe_request(), 2.0, launcher=launch)

    assert caught.value.failure["reason"] == "child_start_failed"
    assert "release" not in events
    assert events == [
        "create",
        "configure",
        "launch",
        "gate_close",
        "job_terminate",
        "job_close",
        "worker_stop",
        "worker_reap",
    ]


@pytest.mark.parametrize("gate_payload", [b"", b"x"])
def test_windows_probe_gate_fails_closed_before_child_execution(gate_payload: bytes) -> None:
    events: list[str] = []

    def child_main(_encoded_request: str) -> int:
        events.append("child")
        return 0

    result = check_published_upgrade._gated_probe_child_main(
        "encoded-request",
        gate=io.BytesIO(gate_payload),
        child_main=child_main,
    )

    assert result == 1
    assert events == []


def test_windows_probe_gate_releases_child_only_after_exact_token() -> None:
    events: list[tuple[str, object]] = []

    class FakeGate(io.BytesIO):
        def read(self, size: int | None = -1, /) -> bytes:
            events.append(("read", size))
            return super().read(size)

    def child_main(encoded_request: str) -> int:
        events.append(("child", encoded_request))
        return 7

    result = check_published_upgrade._gated_probe_child_main(
        "encoded-request",
        gate=FakeGate(check_published_upgrade._WINDOWS_GATE_TOKEN),
        child_main=child_main,
    )

    assert result == 7
    assert events == [("read", 1), ("child", "encoded-request")]


class _FakeManagedProcess:
    pid = 321
    stdin = None

    def __init__(
        self,
        payload: bytes,
        *,
        wait_outcome: str = "success",
        returncode: int = 0,
        events: list[str] | None = None,
    ) -> None:
        self.stdout = io.BytesIO(payload)
        self.returncode: int | None = None
        self._wait_outcome = wait_outcome
        self._completed_returncode = returncode
        self.events = [] if events is None else events

    def wait(self, *, timeout: float) -> int:
        if self.returncode is not None:
            return self.returncode
        if self._wait_outcome == "timeout":
            command = "probe"
            raise subprocess.TimeoutExpired(command, timeout)
        if self._wait_outcome == "error":
            message = r"private C:\probe\worker failure"
            raise OSError(message)
        if self._wait_outcome == "interrupt":
            raise KeyboardInterrupt
        self.returncode = self._completed_returncode
        self.events.append("root_exit")
        return self.returncode

    def poll(self) -> int | None:
        return self.returncode

    def terminate(self) -> None:
        self.events.append("worker_terminate")
        self.returncode = -15

    def kill(self) -> None:
        self.events.append("worker_kill")
        self.returncode = -9


class _RecordingTreeOwner:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.terminate_count = 0
        self.close_count = 0
        self.descendant_owned = True

    def terminate(self) -> None:
        self.terminate_count += 1
        self.events.append("owner_terminate")
        self.descendant_owned = False

    def close(self) -> None:
        self.close_count += 1
        self.events.append("owner_close")


def _fake_managed_probe(
    payload: bytes,
    *,
    wait_outcome: str = "success",
    returncode: int = 0,
) -> tuple[check_published_upgrade._ManagedProbe, _RecordingTreeOwner, list[str]]:
    events: list[str] = []
    process = _FakeManagedProcess(
        payload,
        wait_outcome=wait_outcome,
        returncode=returncode,
        events=events,
    )
    owner = _RecordingTreeOwner(events)
    managed = check_published_upgrade._ManagedProbe(
        process=cast("subprocess.Popen[bytes]", process),
        process_group=None,
        owner=owner,
    )
    return managed, owner, events


def test_probe_closes_tree_owner_after_already_exited_root_on_success() -> None:
    report = _upgrade_report()
    payload = json.dumps({"kind": "report", "report": report}).encode()
    managed, owner, events = _fake_managed_probe(payload)

    observed = check_published_upgrade._run_probe(_probe_request(), 2.0, launcher=lambda _request: managed)

    assert observed == report
    assert events == ["root_exit", "owner_terminate", "owner_close"]
    assert owner.terminate_count == 1
    assert owner.close_count == 1
    assert owner.descendant_owned is False


@pytest.mark.parametrize(
    ("payload", "wait_outcome", "returncode", "reason"),
    [
        (b"private malformed child payload", "success", 0, "child_payload_invalid"),
        (b"", "success", 0, "child_payload_invalid"),
        (b"", "success", 23, "child_process_failed"),
        (b"", "timeout", 0, "timeout"),
        (b"", "error", 0, "child_process_failed"),
    ],
)
def test_probe_closes_tree_owner_on_every_finite_failure(
    payload: bytes,
    wait_outcome: str,
    returncode: int,
    reason: str,
) -> None:
    managed, owner, _events = _fake_managed_probe(
        payload,
        wait_outcome=wait_outcome,
        returncode=returncode,
    )

    with pytest.raises(check_published_upgrade._ProbeExecutorError) as caught:
        check_published_upgrade._run_probe(_probe_request(), 2.0, launcher=lambda _request: managed)

    assert caught.value.failure["reason"] == reason
    assert owner.terminate_count == 1
    assert owner.close_count == 1
    assert "private" not in json.dumps(caught.value.failure)


def test_probe_closes_tree_owner_before_propagating_control_flow() -> None:
    managed, owner, _events = _fake_managed_probe(b"", wait_outcome="interrupt")

    with pytest.raises(KeyboardInterrupt):
        check_published_upgrade._run_probe(_probe_request(), 2.0, launcher=lambda _request: managed)

    assert owner.terminate_count == 1
    assert owner.close_count == 1


def test_probe_cleanup_retries_retained_owner_after_close_failure() -> None:
    report = _upgrade_report()
    events: list[str] = []
    private_detail = "private close failure"

    class RetryableOwner:
        def __init__(self) -> None:
            self.close_count = 0

        def terminate(self) -> None:
            events.append("owner_terminate")

        def close(self) -> None:
            self.close_count += 1
            events.append("owner_close")
            if self.close_count == 1:
                raise windows_job.WindowsJobError(private_detail)

    process = _FakeManagedProcess(
        json.dumps({"kind": "report", "report": report}).encode(),
        events=events,
    )
    owner = RetryableOwner()
    managed = check_published_upgrade._ManagedProbe(
        process=cast("subprocess.Popen[bytes]", process),
        process_group=None,
        owner=owner,
    )

    with pytest.raises(check_published_upgrade._ProbeExecutorError) as caught:
        check_published_upgrade._run_probe(_probe_request(), 2.0, launcher=lambda _request: managed)

    assert caught.value.failure["reason"] == "child_process_failed"
    assert events == [
        "root_exit",
        "owner_terminate",
        "owner_close",
        "owner_terminate",
        "owner_close",
    ]


def test_probe_terminate_failure_still_closes_owner_with_finite_failure() -> None:
    report = _upgrade_report()
    events: list[str] = []
    private_detail = r"private C:\probe termination failure"

    class TerminateFailingOwner:
        def terminate(self) -> None:
            events.append("owner_terminate")
            raise OSError(private_detail)

        def close(self) -> None:
            events.append("owner_close")

    process = _FakeManagedProcess(
        json.dumps({"kind": "report", "report": report}).encode(),
        events=events,
    )
    managed = check_published_upgrade._ManagedProbe(
        process=cast("subprocess.Popen[bytes]", process),
        process_group=None,
        owner=TerminateFailingOwner(),
    )

    with pytest.raises(check_published_upgrade._ProbeExecutorError) as caught:
        check_published_upgrade._run_probe(_probe_request(), 2.0, launcher=lambda _request: managed)

    assert caught.value.failure["reason"] == "child_process_failed"
    assert "private" not in json.dumps(caught.value.failure)
    assert events == ["root_exit", "owner_terminate", "owner_close"]


def test_probe_cleanup_base_exception_still_closes_and_reaps_worker() -> None:
    events: list[str] = []

    class InterruptingOwner:
        def terminate(self) -> None:
            events.append("owner_terminate")
            raise KeyboardInterrupt

        def close(self) -> None:
            events.append("owner_close")

    process = _FakeManagedProcess(b"", wait_outcome="timeout", events=events)
    managed = check_published_upgrade._ManagedProbe(
        process=cast("subprocess.Popen[bytes]", process),
        process_group=None,
        owner=InterruptingOwner(),
    )

    with pytest.raises(KeyboardInterrupt):
        check_published_upgrade._run_probe(_probe_request(), 0.01, launcher=lambda _request: managed)

    assert events == [
        "owner_terminate",
        "owner_close",
        "worker_terminate",
    ]
    assert process.returncode == -15


def test_probe_never_taskkills_an_already_exited_pid_after_owner_close_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = _upgrade_report()
    events: list[str] = []
    private_detail = "private close failure"

    class UncloseableOwner:
        def terminate(self) -> None:
            events.append("owner_terminate")

        def close(self) -> None:
            events.append("owner_close")
            raise OSError(private_detail)

    process = _FakeManagedProcess(
        json.dumps({"kind": "report", "report": report}).encode(),
        events=events,
    )
    managed = check_published_upgrade._ManagedProbe(
        process=cast("subprocess.Popen[bytes]", process),
        process_group=None,
        owner=UncloseableOwner(),
    )
    monkeypatch.setattr(check_published_upgrade.os, "name", "nt")
    monkeypatch.setattr(
        check_published_upgrade,
        "_kill_windows_process_tree",
        lambda _pid: events.append("taskkill") or True,
    )

    with pytest.raises(check_published_upgrade._ProbeExecutorError) as caught:
        check_published_upgrade._run_probe(_probe_request(), 2.0, launcher=lambda _request: managed)

    assert caught.value.failure["reason"] == "child_process_failed"
    assert events == [
        "root_exit",
        "owner_terminate",
        "owner_close",
        "owner_terminate",
        "owner_close",
    ]


def test_windows_assignment_failure_keeps_gate_closed_and_reaps_worker() -> None:
    assert windows_job is not None
    events: list[str] = []
    private_detail = r"AssignProcessToJobObject failed for C:\private\probe handle 0x1234"

    class FakeWinApi:
        def create_job(self) -> object:
            events.append("create")
            return 41

        def configure_kill_on_close(self, job_handle: object) -> None:
            assert job_handle == 41
            events.append("configure")

        def assign_process(self, job_handle: object, process_handle: object) -> None:
            assert (job_handle, process_handle) == (41, 654)
            events.append("assign")
            raise OSError(private_detail)

        def terminate_job(self, job_handle: object, exit_code: int) -> None:
            assert (job_handle, exit_code) == (41, windows_job._JOB_TERMINATION_EXIT_CODE)
            events.append("job_terminate")

        def close_handle(self, handle: object) -> None:
            assert handle == 41
            events.append("job_close")

    class FakeGate:
        def write(self, _data: bytes) -> int:
            events.append("release")
            return 1

        def flush(self) -> None:
            events.append("flush")

        def close(self) -> None:
            events.append("gate_close")

    class FakeProcess:
        pid = 321
        _handle = 654
        stdin = FakeGate()
        stdout = io.BytesIO()
        returncode: int | None = None

        def poll(self) -> int | None:
            return self.returncode

        def terminate(self) -> None:
            events.append("worker_stop")
            self.returncode = -15

        def kill(self) -> None:
            events.append("worker_kill")
            self.returncode = -9

        def wait(self, *, timeout: float) -> int:
            assert timeout <= check_published_upgrade._PROCESS_KILL_GRACE_SECONDS
            events.append("worker_reap")
            assert self.returncode is not None
            return self.returncode

    def create_owner() -> windows_job.WindowsJobOwner:
        return windows_job.create_windows_job_owner(api=FakeWinApi())

    def popen(_command: list[str], **_kwargs: object) -> subprocess.Popen[bytes]:
        events.append("launch")
        return cast("subprocess.Popen[bytes]", FakeProcess())

    def launch(request: check_published_upgrade._ProbeRequest) -> check_published_upgrade._ManagedProbe:
        return check_published_upgrade._launch_windows_probe_process(
            request,
            owner_factory=create_owner,
            popen=popen,
        )

    with pytest.raises(check_published_upgrade._ProbeExecutorError) as caught:
        check_published_upgrade._run_probe(_probe_request(), 2.0, launcher=launch)

    assert caught.value.failure["reason"] == "child_start_failed"
    assert private_detail not in json.dumps(caught.value.failure)
    assert "release" not in events
    assert events == [
        "create",
        "configure",
        "launch",
        "assign",
        "gate_close",
        "job_terminate",
        "job_close",
        "worker_stop",
        "worker_reap",
    ]


@pytest.mark.skipif(os.name != "nt", reason="real Windows Job Object descendant assertion")
def test_windows_job_owner_kills_descendant_after_root_exit(tmp_path: Path) -> None:
    descendant_pid_file = tmp_path / "descendant.pid"
    escaped_marker = tmp_path / "descendant-escaped.txt"
    descendant_code = (
        "import pathlib,time;"
        "time.sleep(1.0);"
        f"pathlib.Path({str(escaped_marker)!r}).write_text('escaped',encoding='utf-8')"
    )
    worker_code = "\n".join(
        [
            "import pathlib,subprocess,sys",
            "if sys.stdin.buffer.read(1) != b'\\x00': raise SystemExit(2)",
            (
                f"child=subprocess.Popen([{sys.executable!r},'-c',{descendant_code!r}],"
                "stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)"
            ),
            f"pathlib.Path({str(descendant_pid_file)!r}).write_text(str(child.pid),encoding='utf-8')",
        ]
    )
    owner = windows_job.create_windows_job_owner()
    process = subprocess.Popen(  # noqa: S603 - fixed local Windows Job Object integration child.
        [sys.executable, "-c", worker_code],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    descendant_pid: int | None = None
    try:
        owner.assign(windows_job.require_popen_process_handle(process))
        assert process.stdin is not None
        process.stdin.write(check_published_upgrade._WINDOWS_GATE_TOKEN)
        process.stdin.close()
        process.wait(timeout=2.0)
        descendant_pid = int(descendant_pid_file.read_text(encoding="utf-8"))

        owner.terminate()
        owner.close()
        time.sleep(1.5)

        assert process.returncode == 0
        assert not escaped_marker.exists()
    finally:
        with contextlib.suppress(windows_job.WindowsJobError):
            owner.close()
        if process.poll() is None:
            process.kill()
            process.wait(timeout=1.0)
        if descendant_pid is not None:
            check_published_upgrade._kill_windows_process_tree(descendant_pid)


def test_windows_tree_kill_reports_unavailable_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable(_command: list[str], **_kwargs: object) -> None:
        raise FileNotFoundError

    monkeypatch.setattr(check_published_upgrade.subprocess, "run", unavailable)

    assert check_published_upgrade._kill_windows_process_tree(321) is False


def test_windows_watchdog_attempts_tree_kill_before_worker_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []

    class FakeProcess:
        pid = 321

        def poll(self) -> None:
            return None

        def kill(self) -> None:
            events.append("worker_kill")

        def wait(self, *, timeout: float) -> None:
            del timeout
            events.append("worker_reap")

    def kill_tree(pid: int) -> bool:
        assert pid == 321
        events.append("tree_kill")
        return False

    monkeypatch.setattr(check_published_upgrade.os, "name", "nt")
    monkeypatch.setattr(check_published_upgrade, "_kill_windows_process_tree", kill_tree)

    process = cast("subprocess.Popen[bytes]", FakeProcess())
    check_published_upgrade._stop_probe_process(process, process_group=None)

    assert events == ["tree_kill", "worker_kill", "worker_reap"]


def test_windows_job_cleanup_reaps_after_second_kill_before_reader_join(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    wait_calls = 0

    class FakeProcess:
        pid = 321
        stdin = None
        stdout = io.BytesIO()
        returncode: int | None = None

        def poll(self) -> int | None:
            return self.returncode

        def kill(self) -> None:
            events.append("worker_kill")

        def wait(self, *, timeout: float) -> int:
            nonlocal wait_calls
            assert timeout <= check_published_upgrade._PROCESS_KILL_GRACE_SECONDS
            wait_calls += 1
            if wait_calls < 3:
                events.append("wait_timeout")
                command = "probe"
                raise subprocess.TimeoutExpired(command, timeout)
            events.append("worker_reap")
            self.returncode = -9
            return self.returncode

    monkeypatch.setattr(check_published_upgrade.os, "name", "nt")
    monkeypatch.setattr(
        check_published_upgrade,
        "_finish_child_reader",
        lambda _process, _reader: events.append("reader_join"),
    )
    process = cast("subprocess.Popen[bytes]", FakeProcess())
    managed = check_published_upgrade._ManagedProbe(
        process=process,
        process_group=None,
        owner=check_published_upgrade._NoopProcessTreeOwner(),
    )

    assert check_published_upgrade._finalize_managed_probe(
        managed,
        reader=cast("threading.Thread", object()),
        stop_worker=True,
    )

    assert events == [
        "wait_timeout",
        "worker_kill",
        "wait_timeout",
        "worker_kill",
        "worker_reap",
        "reader_join",
    ]


def test_windows_second_kill_base_exception_still_performs_final_reap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    kill_calls = 0
    wait_calls = 0

    class FakeProcess:
        pid = 321

        def poll(self) -> None:
            return None

        def kill(self) -> None:
            nonlocal kill_calls
            kill_calls += 1
            events.append("worker_kill")
            if kill_calls == 2:
                raise KeyboardInterrupt

        def wait(self, *, timeout: float) -> int:
            nonlocal wait_calls
            wait_calls += 1
            events.append("worker_wait")
            if wait_calls < 3:
                command = "probe"
                raise subprocess.TimeoutExpired(command, timeout)
            return -9

    monkeypatch.setattr(check_published_upgrade.os, "name", "nt")
    process = cast("subprocess.Popen[bytes]", FakeProcess())

    with pytest.raises(KeyboardInterrupt):
        check_published_upgrade._stop_probe_process(
            process,
            process_group=None,
            windows_tree_fallback=False,
        )

    assert events == [
        "worker_wait",
        "worker_kill",
        "worker_wait",
        "worker_kill",
        "worker_wait",
    ]


def test_windows_pre_kill_wait_base_exception_still_kills_and_reaps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    wait_calls = 0

    class FakeProcess:
        pid = 321
        returncode: int | None = None

        def poll(self) -> int | None:
            return self.returncode

        def kill(self) -> None:
            events.append("worker_kill")

        def wait(self, *, timeout: float) -> int:
            nonlocal wait_calls
            assert timeout > 0
            wait_calls += 1
            if wait_calls == 1:
                events.append("wait_interrupt")
                raise KeyboardInterrupt
            events.append("worker_reap")
            self.returncode = -9
            return self.returncode

    monkeypatch.setattr(check_published_upgrade.os, "name", "nt")
    process = cast("subprocess.Popen[bytes]", FakeProcess())

    with pytest.raises(KeyboardInterrupt):
        check_published_upgrade._stop_probe_process(
            process,
            process_group=None,
            windows_tree_fallback=False,
        )

    assert events == ["wait_interrupt", "worker_kill", "worker_reap"]


def test_reader_join_base_exception_still_closes_pipe_and_retries_join() -> None:
    events: list[str] = []

    class FakeReader:
        join_calls = 0

        def join(self, *, timeout: float) -> None:
            assert timeout == check_published_upgrade._PROCESS_KILL_GRACE_SECONDS
            self.join_calls += 1
            events.append("reader_join")
            if self.join_calls == 1:
                raise KeyboardInterrupt

        def is_alive(self) -> bool:
            return self.join_calls < 2

    class FakeStream(io.BytesIO):
        def close(self) -> None:
            events.append("pipe_close")
            super().close()

    class FakeProcess:
        stdout = FakeStream()

    with pytest.raises(KeyboardInterrupt):
        check_published_upgrade._finish_child_reader(
            cast("subprocess.Popen[bytes]", FakeProcess()),
            cast("threading.Thread", FakeReader()),
        )

    assert events == ["reader_join", "pipe_close", "reader_join"]


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


_ATOMIC_WRITER_CASES = (
    pytest.param(
        "_write_atomic_posix",
        id="posix",
        marks=pytest.mark.skipif(os.name != "posix", reason="POSIX dirfd writer"),
    ),
    pytest.param("_write_atomic_fallback", id="fallback"),
)


def test_public_atomic_text_writer_delegates_to_hardened_writer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[Path, str]] = []

    def record_write(path: Path, content: str) -> None:
        calls.append((path, content))

    monkeypatch.setattr(check_published_upgrade, "_write_atomic", record_write)
    output = tmp_path / "upgrade.json"

    check_published_upgrade.write_atomic_text(output, "proof\n")

    assert calls == [(output, "proof\n")]


@pytest.mark.parametrize(
    "writer_name",
    _ATOMIC_WRITER_CASES,
)
@pytest.mark.parametrize(
    ("destination_state", "failing_fsync"),
    [
        ("absent", 1),
        ("absent", 2),
        ("existing", 1),
        ("existing", 2),
        ("existing", 3),
    ],
)
def test_fsync_failure_through_commit_rolls_back_and_cleans_sidecars(
    writer_name: str,
    destination_state: str,
    failing_fsync: int,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "upgrade.json"
    if destination_state == "existing":
        output.write_text("previous evidence\n", encoding="utf-8")
    original_fsync = os.fsync
    fsync_calls = 0

    def fail_selected_fsync(file_descriptor: int) -> None:
        nonlocal fsync_calls
        fsync_calls += 1
        if fsync_calls == failing_fsync:
            message = "forced pre-commit fsync failure"
            raise OSError(message)
        original_fsync(file_descriptor)

    monkeypatch.setattr(check_published_upgrade.os, "fsync", fail_selected_fsync)
    writer = getattr(check_published_upgrade, writer_name)

    with pytest.raises(OSError, match="pre-commit fsync"):
        writer(output, "new evidence\n")

    assert fsync_calls >= failing_fsync
    if destination_state == "existing":
        assert output.read_text(encoding="utf-8") == "previous evidence\n"
        assert list(tmp_path.iterdir()) == [output]
    else:
        assert not output.exists()
        assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "writer_name",
    _ATOMIC_WRITER_CASES,
)
def test_existing_output_commits_before_best_effort_backup_cleanup(
    writer_name: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "upgrade.json"
    output.write_text("previous evidence\n", encoding="utf-8")
    events: list[str] = []
    original_fsync = os.fsync
    original_replace = os.replace
    original_unlink = os.unlink

    def recording_fsync(file_descriptor: int) -> None:
        descriptor_kind = "dir_fsync" if stat.S_ISDIR(os.fstat(file_descriptor).st_mode) else "file_fsync"
        events.append(descriptor_kind)
        original_fsync(file_descriptor)

    def recording_replace(
        source: str | os.PathLike[str],
        target: str | os.PathLike[str],
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
    ) -> None:
        events.append("replace")
        original_replace(source, target, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)

    def recording_unlink(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        if "published-upgrade-backup" in os.fsdecode(path):
            events.append("backup_unlink")
        original_unlink(path, dir_fd=dir_fd)

    monkeypatch.setattr(check_published_upgrade.os, "fsync", recording_fsync)
    monkeypatch.setattr(check_published_upgrade.os, "replace", recording_replace)
    monkeypatch.setattr(check_published_upgrade.os, "unlink", recording_unlink)
    writer = getattr(check_published_upgrade, writer_name)

    writer(output, "new evidence\n")

    assert output.read_text(encoding="utf-8") == "new evidence\n"
    assert events == ["file_fsync", "dir_fsync", "replace", "dir_fsync", "backup_unlink"]
    assert list(tmp_path.iterdir()) == [output]


@pytest.mark.parametrize(
    "writer_name",
    _ATOMIC_WRITER_CASES,
)
def test_backup_unlink_failure_after_commit_does_not_fail_report(
    writer_name: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "upgrade.json"
    output.write_text("previous evidence\n", encoding="utf-8")
    original_unlink = os.unlink
    failed_attempts = 0

    def fail_backup_unlink(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal failed_attempts
        if "published-upgrade-backup" in os.fsdecode(path):
            failed_attempts += 1
            message = "forced post-commit backup cleanup failure"
            raise OSError(message)
        original_unlink(path, dir_fd=dir_fd)

    monkeypatch.setattr(check_published_upgrade.os, "unlink", fail_backup_unlink)
    writer = getattr(check_published_upgrade, writer_name)

    writer(output, "new evidence\n")

    assert failed_attempts >= 1
    assert output.read_text(encoding="utf-8") == "new evidence\n"
    assert len(list(tmp_path.glob(".published-upgrade-backup-*.tmp"))) == 1


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


@pytest.mark.skipif(os.name != "posix", reason="POSIX missing-parent race assertion")
def test_posix_writer_does_not_retry_parent_created_after_missing_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = tmp_path / "parent"
    parent.mkdir()
    replacement = parent / "missing"
    output = replacement / "upgrade.json"
    original_open = os.open
    replacement_created = False

    def create_replacement_after_missing_open(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal replacement_created
        try:
            return original_open(path, flags, mode, dir_fd=dir_fd)
        except FileNotFoundError:
            if path == "missing" and dir_fd is not None and not replacement_created:
                replacement.mkdir()
                replacement_created = True
            raise

    monkeypatch.setattr(check_published_upgrade.os, "open", create_replacement_after_missing_open)

    with pytest.raises(FileNotFoundError):
        check_published_upgrade._write_atomic_posix(output, "proof\n")

    assert replacement_created is True
    assert list(replacement.iterdir()) == []


def test_non_posix_fallback_writes_and_rejects_symlink_ancestors(tmp_path: Path) -> None:
    output = tmp_path / "evidence" / "upgrade.json"
    output.parent.mkdir()
    check_published_upgrade._write_atomic_fallback(output, "proof\n")
    assert output.read_text(encoding="utf-8") == "proof\n"

    target_directory = tmp_path / "target"
    target_directory.mkdir()
    linked_directory = tmp_path / "linked"
    linked_directory.symlink_to(target_directory, target_is_directory=True)

    with pytest.raises(OSError, match="non-symlink directory"):
        check_published_upgrade._write_atomic_fallback(linked_directory / "upgrade.json", "other\n")

    assert not (target_directory / "upgrade.json").exists()


def test_atomic_write_help_acknowledges_non_posix_race_limitations() -> None:
    documentation = check_published_upgrade.write_atomic_text.__doc__ or ""

    assert "best-effort" in documentation
    assert "non-POSIX" in documentation
    assert "without following output path symlinks" not in documentation


def test_non_posix_fallback_rejects_missing_parent_without_creation(tmp_path: Path) -> None:
    output = tmp_path / "missing" / "upgrade.json"

    with pytest.raises(OSError, match="parent directory must already exist"):
        check_published_upgrade._write_atomic_fallback(output, "proof\n")

    assert not output.parent.exists()
    assert list(tmp_path.iterdir()) == []
