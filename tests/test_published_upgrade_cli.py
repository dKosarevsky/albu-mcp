from __future__ import annotations

import asyncio
import json
import os
import sys
from collections.abc import Callable
from pathlib import Path

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
    PublishedUpgradeConfig,
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

    async def fake_probe(config: PublishedUpgradeConfig) -> UpgradeProofReport:
        assert config.from_version == "1.20.0"
        assert config.to_version == "1.21.0"
        return expected

    monkeypatch.setattr(check_published_upgrade, "run_published_upgrade", fake_probe)
    monkeypatch.setattr(check_published_upgrade, "check_pypi_version", lambda **_kwargs: None)
    return expected


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
    monkeypatch.setattr(check_published_upgrade, "run_published_upgrade", unexpected_call)

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
    monkeypatch.setattr(check_published_upgrade, "run_published_upgrade", unexpected_call)

    with pytest.raises(SystemExit) as caught:
        check_published_upgrade.main(["--from-version", "1.20.0", "--to-version", "1.21.0", option, value])

    assert caught.value.code == 2
    assert external_calls == 0


def test_dry_run_prints_three_attested_pinned_commands_without_external_calls(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def unexpected_call(*_args: object, **_kwargs: object) -> None:
        raise AssertionError

    monkeypatch.setattr(check_published_upgrade, "check_pypi_version", unexpected_call)
    monkeypatch.setattr(check_published_upgrade, "run_published_upgrade", unexpected_call)
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

    error = check_published_upgrade.check_pypi_version(
        package=PACKAGE,
        version="1.21.0",
        timeout_seconds=1.0,
    )

    assert error == "PyPI version endpoint is not visible yet."
    assert sensitive_detail not in error


def test_pypi_check_does_not_echo_arbitrary_response_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sensitive_detail = "private-returned-version-token"

    class Response:
        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps({"info": {"version": sensitive_detail}}).encode()

    monkeypatch.setattr(check_published_package_smoke.urllib.request, "urlopen", lambda *_args, **_kwargs: Response())

    error = check_published_upgrade.check_pypi_version(
        package=PACKAGE,
        version="1.21.0",
        timeout_seconds=1.0,
    )

    assert error == "PyPI version endpoint did not confirm the requested exact version."
    assert sensitive_detail not in error


def test_pypi_versions_are_retried_deterministically_without_final_sleep(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    attempts: dict[str, int] = {}
    calls: list[str] = []
    sleeps: list[float] = []
    probe_calls = 0

    def fake_check(*, package: str, version: str, timeout_seconds: float) -> str | None:
        assert package == PACKAGE
        assert timeout_seconds == 2.0
        calls.append(version)
        attempts[version] = attempts.get(version, 0) + 1
        if version == "1.20.0" and attempts[version] >= 2:
            return None
        return "untrusted injected detail"

    async def unexpected_probe(_config: PublishedUpgradeConfig) -> UpgradeProofReport:
        nonlocal probe_calls
        probe_calls += 1
        raise AssertionError

    monkeypatch.setattr(check_published_upgrade, "check_pypi_version", fake_check)
    monkeypatch.setattr(check_published_upgrade, "run_published_upgrade", unexpected_probe)
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
    assert "untrusted injected detail" not in json.dumps(failure)


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

    def fake_fsync(_file_descriptor: int) -> None:
        events.append("fsync")

    def recording_replace(source: str | os.PathLike[str], target: str | os.PathLike[str]) -> None:
        events.append("replace")
        original_replace(source, target)

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
    assert events == ["fsync", "replace"]
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
            "--output",
            str(output),
        ]
    )

    assert result == 1
    assert output.read_text(encoding="utf-8") == "previous evidence\n"
    failure = json.loads(capsys.readouterr().err)
    assert failure == report
    assert failure["failures"][0]["code"] == "surface_removed"


def test_probe_timeout_fails_closed_without_replacing_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def blocked_probe(_config: PublishedUpgradeConfig) -> UpgradeProofReport:
        await asyncio.Event().wait()
        raise AssertionError

    monkeypatch.setattr(check_published_upgrade, "run_published_upgrade", blocked_probe)
    monkeypatch.setattr(check_published_upgrade, "check_pypi_version", lambda **_kwargs: None)
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


def test_python_310_asyncio_timeout_is_classified_once_through_exception_group(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class SimulatedAsyncioTimeoutError(Exception):
        pass

    def failed_probe(_config: PublishedUpgradeConfig, _timeout_seconds: float) -> UpgradeProofReport:
        message = "private timeout group"
        raise RuntimeExceptionGroup(message, [SimulatedAsyncioTimeoutError("private timeout detail")])

    monkeypatch.setattr(check_published_upgrade.asyncio, "TimeoutError", SimulatedAsyncioTimeoutError)
    monkeypatch.setattr(check_published_upgrade, "_run_probe", failed_probe)
    monkeypatch.setattr(check_published_upgrade, "check_pypi_version", lambda **_kwargs: None)

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
    async def failed_probe(_config: PublishedUpgradeConfig) -> UpgradeProofReport:
        raise PublishedUpgradeRuntimeError(
            phase=RuntimePhase.NEGOTIATION,
            code=RuntimeCode.NEGOTIATION_FAILED,
            diagnostic=StderrCategory.OTHER,
        )

    monkeypatch.setattr(check_published_upgrade, "run_published_upgrade", failed_probe)
    monkeypatch.setattr(check_published_upgrade, "check_pypi_version", lambda **_kwargs: None)

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

    error = check_published_upgrade.check_pypi_version(
        package=PACKAGE,
        version="1.21.0",
        timeout_seconds=1.0,
    )

    assert error == "PyPI version endpoint is not visible yet."
    assert sensitive_detail not in error


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
    def failed_probe(_config: PublishedUpgradeConfig, _timeout_seconds: float) -> UpgradeProofReport:
        raise error_factory()

    monkeypatch.setattr(check_published_upgrade, "_run_probe", failed_probe)
    monkeypatch.setattr(check_published_upgrade, "check_pypi_version", lambda **_kwargs: None)

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

    def interrupted_probe(_config: PublishedUpgradeConfig, _timeout_seconds: float) -> UpgradeProofReport:
        raise error

    monkeypatch.setattr(check_published_upgrade, "_run_probe", interrupted_probe)
    monkeypatch.setattr(check_published_upgrade, "check_pypi_version", lambda **_kwargs: None)

    with pytest.raises((asyncio.CancelledError, KeyboardInterrupt, SystemExit)):
        check_published_upgrade.main(["--from-version", "1.20.0", "--to-version", "1.21.0"])


def test_atomic_write_failure_cleans_temp_and_preserves_existing_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _install_successful_probe(monkeypatch)
    output = tmp_path / "upgrade.json"
    output.write_text("previous evidence\n", encoding="utf-8")
    secret = str(tmp_path / "private-write-token")

    def fail_replace(_source: object, _target: object) -> None:
        raise OSError(secret)

    monkeypatch.setattr(check_published_upgrade.os, "replace", fail_replace)

    result = check_published_upgrade.main(
        [
            "--from-version",
            "1.20.0",
            "--to-version",
            "1.21.0",
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
            "--output",
            str(output),
        ]
    )

    assert result == 1
    assert output.is_symlink()
    assert target.read_text(encoding="utf-8") == "previous evidence\n"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["target.json", "upgrade.json"]
    assert json.loads(capsys.readouterr().err)["failures"][0]["code"] == "output_write_failed"
