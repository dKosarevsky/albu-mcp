"""Prove compatibility between two exact published AlbumentationsX MCP versions."""

from __future__ import annotations

import argparse
import asyncio
import base64
import contextlib
import json
import math
import os
import re
import secrets
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import BinaryIO, Final, Protocol, TypeVar

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcp.types.version import LATEST_MODERN_VERSION

from albumentationsx_mcp.upgrade_proof import (
    UpgradeProofReport,
    serialize_upgrade_proof_report,
    validate_upgrade_proof_report,
)
from scripts.check_published_package_smoke import PyPIVersionResult, PyPIVersionState, check_pypi_version
from scripts.published_upgrade_runtime import (
    PACKAGE,
    PublishedUpgradeConfig,
    PublishedUpgradeRuntimeError,
    RuntimeCode,
    RuntimePhase,
    StderrCategory,
    build_attested_uvx_server_command,
    run_published_upgrade,
)

_SCHEMA_VERSION: Final = "albumentationsx-mcp/published-upgrade-proof/v1"
_EXACT_VERSION: Final = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\Z")
_ISO_DATE: Final = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")
_MAX_VERSION_LENGTH: Final = 128
_MAX_RETRIES: Final = 10
_MAX_RETRY_DELAY_SECONDS: Final = 300.0
_MAX_PYPI_TIMEOUT_SECONDS: Final = 120.0
_MAX_READ_TIMEOUT_SECONDS: Final = 600.0
_MAX_PROBE_TIMEOUT_SECONDS: Final = 3600.0
_MAX_SERIALIZED_REPORT_BYTES: Final = 1024 * 1024
_MAX_CHILD_PAYLOAD_BYTES: Final = _MAX_SERIALIZED_REPORT_BYTES + 4096
_MAX_ENCODED_REQUEST_LENGTH: Final = 4096
_PROCESS_TERMINATE_GRACE_SECONDS: Final = 0.25
_PROCESS_KILL_GRACE_SECONDS: Final = 0.5
_CHILD_MODE: Final = "--published-upgrade-child"
_CHILD_ARG_COUNT: Final = 3
_MAX_OUTPUT_PATH_LENGTH: Final = 4096
_MAX_OUTPUT_COMPONENTS: Final = 64
_MAX_OUTPUT_COMPONENT_LENGTH: Final = 255
_TEMP_FILE_ATTEMPTS: Final = 16
_CHILD_ERROR_REASONS: Final = frozenset({"child_payload_invalid", "child_process_failed", "operational_error"})
_RUNTIME_PHASE_VALUES: Final = frozenset(item.value for item in RuntimePhase)
_RUNTIME_CODE_VALUES: Final = frozenset(item.value for item in RuntimeCode)
_STDERR_CATEGORY_VALUES: Final = frozenset(item.value for item in StderrCategory)


class _PyPIVersionCheck(Protocol):
    def __call__(self, *, package: str, version: str, timeout_seconds: float) -> PyPIVersionResult: ...


@dataclass(frozen=True)
class _PyPIWaitConfig:
    versions: tuple[str, ...]
    retries: int
    delay_seconds: float
    timeout_seconds: float


@dataclass(frozen=True)
class _FailureContext:
    from_version: str
    to_version: str
    observed_on: date


@dataclass(frozen=True)
class _ProbeRequest:
    from_version: str
    to_version: str
    observed_on: str
    read_timeout_seconds: float


@dataclass(frozen=True)
class _PyPIVersionFailure:
    version: str
    state: PyPIVersionState


@dataclass
class _BoundedChildOutput:
    data: bytes = b""
    failed: bool = False


class _ProbeExecutorError(RuntimeError):
    def __init__(self, failure: dict[str, str]) -> None:
        self.failure = dict(failure)
        super().__init__("Published upgrade child execution failed.")


_ProbeLauncher = Callable[[_ProbeRequest], subprocess.Popen[bytes]]
_ExceptionT = TypeVar("_ExceptionT", bound=BaseException)


def validate_exact_version(value: str) -> str:
    """Require the strict public X.Y.Z release grammar used by upgrade evidence."""
    if len(value) > _MAX_VERSION_LENGTH or _EXACT_VERSION.fullmatch(value) is None:
        message = "version must be an exact release version such as 1.21.0"
        raise ValueError(message)
    return value


def build_parser() -> argparse.ArgumentParser:
    """Build the fail-closed operator argument parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-version", required=True, type=_parse_exact_version)
    parser.add_argument("--to-version", required=True, type=_parse_exact_version)
    parser.add_argument("--observed-on", type=_parse_observed_on, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--retries", type=_parse_retries, default=3)
    parser.add_argument("--retry-delay", type=_parse_retry_delay, default=5.0)
    parser.add_argument("--pypi-timeout", type=_parse_pypi_timeout, default=20.0)
    parser.add_argument("--read-timeout", type=_parse_read_timeout, default=120.0)
    parser.add_argument("--probe-timeout", type=_parse_probe_timeout, default=600.0)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the published upgrade proof or print its exact dry-run commands."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        _validate_upgrade_order(args.from_version, args.to_version)
    except ValueError as error:
        parser.error(str(error))

    observed_on = args.observed_on or datetime.now(tz=timezone.utc).date()
    if args.dry_run:
        sys.stdout.write(_serialize_json(_dry_run_payload(args.from_version, args.to_version)))
        return 0

    context = _FailureContext(
        from_version=args.from_version,
        to_version=args.to_version,
        observed_on=observed_on,
    )
    return _execute_upgrade(args, context)


def _execute_upgrade(args: argparse.Namespace, context: _FailureContext) -> int:
    if not _verify_pypi_versions(args, context):
        return 1
    report = _collect_upgrade_report(args, context)
    if report is None:
        return 1
    serialized = _validated_serialized_report(report, context)
    if serialized is None:
        return 1
    content, status = serialized
    return _publish_report(args.output, content=content, status=status, context=context)


def _verify_pypi_versions(args: argparse.Namespace, context: _FailureContext) -> bool:
    try:
        unavailable_versions = _wait_for_pypi_versions(
            _PyPIWaitConfig(
                versions=(args.from_version, args.to_version),
                retries=args.retries,
                delay_seconds=args.retry_delay,
                timeout_seconds=args.pypi_timeout,
            ),
            check_version=check_pypi_version,
            sleep=time.sleep,
        )
    except BaseException as error:
        _raise_control_flow(error)
        if not isinstance(error, Exception):
            raise
        _emit_failure(
            context,
            failures=[
                {
                    "code": "pypi_check_failed",
                    "reason": "operational_error",
                    "remediation": "Retry after checking public PyPI connectivity locally.",
                }
            ],
        )
        return False

    if unavailable_versions:
        failures = [_pypi_failure(item, from_version=args.from_version) for item in unavailable_versions]
        _emit_failure(context, failures=failures)
        return False
    return True


def _collect_upgrade_report(
    args: argparse.Namespace,
    context: _FailureContext,
) -> object | None:
    try:
        report = _run_probe(
            _ProbeRequest(
                from_version=args.from_version,
                to_version=args.to_version,
                observed_on=context.observed_on.isoformat(),
                read_timeout_seconds=args.read_timeout,
            ),
            args.probe_timeout,
        )
    except BaseException as error:  # noqa: BLE001 - AnyIO may wrap runtime failures in base exception groups.
        failure = _probe_failure(error)
        _emit_failure(context, failures=[failure])
        return None
    return report


def _validated_serialized_report(
    report: object,
    context: _FailureContext,
) -> tuple[str, str] | None:
    try:
        validated = validate_upgrade_proof_report(
            report,
            expected_package=PACKAGE,
            expected_from_version=context.from_version,
            expected_to_version=context.to_version,
            expected_observed_on=context.observed_on.isoformat(),
        )
        content = _serialize_report(validated)
    except (TypeError, ValueError):
        _emit_failure(
            context,
            failures=[
                {
                    "code": "probe_execution_failed",
                    "reason": "invalid_report",
                    "remediation": "Retry with a runtime that emits the current upgrade proof schema.",
                }
            ],
        )
        return None
    return content, validated["status"]


def _publish_report(
    output: Path | None,
    *,
    content: str,
    status: str,
    context: _FailureContext,
) -> int:
    if status == "fail":
        sys.stderr.write(content)
        return 1
    if output is None:
        sys.stdout.write(content)
        return 0

    try:
        _write_atomic(output, content)
    except BaseException as error:
        _raise_control_flow(error)
        if not isinstance(error, Exception):
            raise
        _emit_failure(
            context,
            failures=[
                {
                    "code": "output_write_failed",
                    "reason": "operational_error",
                    "remediation": "Choose a regular non-symlink output path in a writable directory and retry.",
                }
            ],
        )
        return 1
    return 0


def _parse_exact_version(value: str) -> str:
    try:
        return validate_exact_version(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from None


def _parse_observed_on(value: str) -> date:
    if _ISO_DATE.fullmatch(value) is None:
        message = "observed-on must be a valid ISO calendar date in YYYY-MM-DD form"
        raise argparse.ArgumentTypeError(message)
    try:
        return date.fromisoformat(value)
    except ValueError:
        message = "observed-on must be a valid ISO calendar date in YYYY-MM-DD form"
        raise argparse.ArgumentTypeError(message) from None


def _parse_retries(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError:
        message = f"retries must be an integer from 1 through {_MAX_RETRIES}"
        raise argparse.ArgumentTypeError(message) from None
    if not 1 <= parsed <= _MAX_RETRIES:
        message = f"retries must be an integer from 1 through {_MAX_RETRIES}"
        raise argparse.ArgumentTypeError(message)
    return parsed


def _parse_retry_delay(value: str) -> float:
    return _parse_bounded_float(
        value,
        label="retry-delay",
        maximum=_MAX_RETRY_DELAY_SECONDS,
        allow_zero=True,
    )


def _parse_pypi_timeout(value: str) -> float:
    return _parse_bounded_float(
        value,
        label="pypi-timeout",
        maximum=_MAX_PYPI_TIMEOUT_SECONDS,
        allow_zero=False,
    )


def _parse_read_timeout(value: str) -> float:
    return _parse_bounded_float(
        value,
        label="read-timeout",
        maximum=_MAX_READ_TIMEOUT_SECONDS,
        allow_zero=False,
    )


def _parse_probe_timeout(value: str) -> float:
    return _parse_bounded_float(
        value,
        label="probe-timeout",
        maximum=_MAX_PROBE_TIMEOUT_SECONDS,
        allow_zero=False,
    )


def _parse_bounded_float(value: str, *, label: str, maximum: float, allow_zero: bool) -> float:
    qualifier = "nonnegative" if allow_zero else "positive"
    message = f"{label} must be a finite {qualifier} number no greater than {maximum:g}"
    try:
        parsed = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(message) from None
    if not math.isfinite(parsed) or parsed < 0 or (not allow_zero and parsed == 0) or parsed > maximum:
        raise argparse.ArgumentTypeError(message)
    return parsed


def _validate_upgrade_order(from_version: str, to_version: str) -> None:
    if _version_tuple(to_version) <= _version_tuple(from_version):
        message = "to-version must be strictly newer than from-version"
        raise ValueError(message)


def _version_tuple(value: str) -> tuple[int, int, int]:
    match = _EXACT_VERSION.fullmatch(value)
    if match is None:
        message = "version must be validated before comparison"
        raise ValueError(message)
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def _dry_run_payload(from_version: str, to_version: str) -> dict[str, object]:
    return {
        "commands": [
            {
                "server_version": from_version,
                "client_mode": "legacy",
                "command": build_attested_uvx_server_command(from_version),
            },
            {
                "server_version": to_version,
                "client_mode": "legacy",
                "command": build_attested_uvx_server_command(to_version),
            },
            {
                "server_version": to_version,
                "client_mode": LATEST_MODERN_VERSION,
                "command": build_attested_uvx_server_command(to_version),
            },
        ]
    }


def _wait_for_pypi_versions(
    config: _PyPIWaitConfig,
    *,
    check_version: _PyPIVersionCheck,
    sleep: Callable[[float], None],
) -> tuple[_PyPIVersionFailure, ...]:
    unavailable: list[_PyPIVersionFailure] = []
    for version in dict.fromkeys(config.versions):
        for attempt in range(config.retries):
            result = check_version(package=PACKAGE, version=version, timeout_seconds=config.timeout_seconds)
            if result.available:
                break
            if not result.retryable:
                unavailable.append(_PyPIVersionFailure(version=version, state=result.state))
                return tuple(unavailable)
            if attempt + 1 < config.retries:
                sleep(config.delay_seconds)
        else:
            unavailable.append(_PyPIVersionFailure(version=version, state=PyPIVersionState.RETRYABLE_UNAVAILABLE))
    return tuple(unavailable)


def _pypi_failure(failure: _PyPIVersionFailure, *, from_version: str) -> dict[str, str]:
    scope = "from_version" if failure.version == from_version else "to_version"
    if failure.state is PyPIVersionState.TERMINAL_VERSION_MISMATCH:
        return {
            "code": "pypi_version_mismatch",
            "scope": scope,
            "remediation": "Verify the exact public PyPI release version before running the upgrade proof.",
        }
    if failure.state is PyPIVersionState.TERMINAL_MALFORMED:
        return {
            "code": "pypi_response_invalid",
            "scope": scope,
            "remediation": "Retry after the public PyPI version endpoint returns a bounded valid response.",
        }
    return {
        "code": "pypi_version_unavailable",
        "scope": scope,
        "remediation": "Retry after the exact release is visible on the public PyPI version endpoint.",
    }


# Isolated probe watchdog


def _run_probe(
    request: _ProbeRequest,
    timeout_seconds: float,
    *,
    launcher: _ProbeLauncher | None = None,
) -> object:
    deadline = time.monotonic() + timeout_seconds
    try:
        process = (launcher or _launch_probe_process)(request)
    except BaseException as error:  # noqa: BLE001 - nested control-flow exceptions must survive test seams.
        _raise_control_flow(error)
        raise _ProbeExecutorError(_child_failure("child_start_failed")) from None
    process_group = process.pid if os.name == "posix" else None
    if process.stdout is None:
        _stop_probe_process(process, process_group=process_group)
        raise _ProbeExecutorError(_child_failure("child_start_failed"))

    output = _BoundedChildOutput()
    reader = threading.Thread(
        target=_read_bounded_child_output,
        args=(process.stdout, output),
        daemon=True,
    )
    reader.start()
    try:
        remaining = max(0.0, deadline - time.monotonic())
        process.wait(timeout=remaining)
    except subprocess.TimeoutExpired:
        _stop_probe_process(process, process_group=process_group)
        _finish_child_reader(process, reader)
        raise _ProbeExecutorError(_child_failure("timeout")) from None
    except BaseException as error:  # noqa: BLE001 - nested control-flow exceptions must survive test seams.
        _stop_probe_process(process, process_group=process_group)
        _finish_child_reader(process, reader)
        _raise_control_flow(error)
        raise _ProbeExecutorError(_child_failure("child_process_failed")) from None
    _force_kill_process_tree(process, process_group=process_group)
    _finish_child_reader(process, reader)

    if output.failed or len(output.data) > _MAX_CHILD_PAYLOAD_BYTES:
        raise _ProbeExecutorError(_child_failure("child_payload_invalid"))
    if process.returncode != 0:
        raise _ProbeExecutorError(_child_failure("child_process_failed"))
    return _parse_child_payload(output.data)


def _launch_probe_process(request: _ProbeRequest) -> subprocess.Popen[bytes]:
    encoded_request = _encode_probe_request(request)
    return subprocess.Popen(  # noqa: S603 - fixed interpreter and local script path.
        [sys.executable, str(Path(__file__).resolve()), _CHILD_MODE, encoded_request],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        start_new_session=os.name == "posix",
        creationflags=(getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0),
    )


def _read_bounded_child_output(stream: BinaryIO, output: _BoundedChildOutput) -> None:
    try:
        data = stream.read(_MAX_CHILD_PAYLOAD_BYTES + 1)
        if type(data) is not bytes:
            output.failed = True
            return
        output.data = data
    except Exception:  # noqa: BLE001 - reader exposes only a finite failure bit.
        output.failed = True
    finally:
        try:
            stream.close()
        except Exception:  # noqa: BLE001 - process outcome remains finite.
            output.failed = True


def _finish_child_reader(process: subprocess.Popen[bytes], reader: threading.Thread) -> None:
    reader.join(timeout=_PROCESS_KILL_GRACE_SECONDS)
    if reader.is_alive() and process.stdout is not None:
        with contextlib.suppress(OSError):
            process.stdout.close()
        reader.join(timeout=_PROCESS_KILL_GRACE_SECONDS)


def _stop_probe_process(process: subprocess.Popen[bytes], *, process_group: int | None) -> None:
    if os.name == "nt" and process_group is None:
        _kill_windows_process_tree(process.pid)
    else:
        if process.poll() is None:
            _signal_probe_process(process, process_group=process_group, terminate=True)
            with contextlib.suppress(subprocess.TimeoutExpired):
                process.wait(timeout=_PROCESS_TERMINATE_GRACE_SECONDS)
        _force_kill_process_tree(process, process_group=process_group)
    if process.poll() is None:
        with contextlib.suppress(OSError):
            process.kill()
        try:
            process.wait(timeout=_PROCESS_KILL_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(OSError):
                process.kill()


def _signal_probe_process(
    process: subprocess.Popen[bytes],
    *,
    process_group: int | None,
    terminate: bool,
) -> None:
    if process_group is not None:
        try:
            os.killpg(process_group, signal.SIGTERM if terminate else signal.SIGKILL)
        except OSError:
            pass
        else:
            return
    try:
        if terminate:
            process.terminate()
        else:
            process.kill()
    except OSError:
        return


def _force_kill_process_tree(process: subprocess.Popen[bytes], *, process_group: int | None) -> bool:
    if process_group is not None:
        try:
            os.killpg(process_group, signal.SIGKILL)
        except OSError:
            return False
        return True
    if os.name == "nt":
        return _kill_windows_process_tree(process.pid)
    return False


def _kill_windows_process_tree(pid: int) -> bool:
    """Best-effort bounded tree kill; callers still kill/reap the worker when taskkill is unavailable."""
    try:
        completed = subprocess.run(  # noqa: S603 - fixed Windows system command and numeric PID.
            ["taskkill", "/PID", str(pid), "/T", "/F"],  # noqa: S607 - documented system utility lookup.
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=_PROCESS_KILL_GRACE_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return completed.returncode == 0


def _encode_probe_request(request: _ProbeRequest) -> str:
    payload = json.dumps(
        {
            "from_version": request.from_version,
            "to_version": request.to_version,
            "observed_on": request.observed_on,
            "read_timeout_seconds": request.read_timeout_seconds,
        },
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii")


def _decode_probe_request(encoded: str) -> _ProbeRequest:
    if type(encoded) is not str or len(encoded) > _MAX_ENCODED_REQUEST_LENGTH:
        raise _ProbeExecutorError(_child_failure("child_payload_invalid"))
    try:
        raw = base64.b64decode(encoded.encode("ascii"), altchars=b"-_", validate=True)
        data = json.loads(raw.decode("utf-8"))
    except Exception as error:
        raise _ProbeExecutorError(_child_failure("child_payload_invalid")) from error
    expected_keys = {"from_version", "to_version", "observed_on", "read_timeout_seconds"}
    if type(data) is not dict or len(data) != len(expected_keys) or set(data) != expected_keys:
        raise _ProbeExecutorError(_child_failure("child_payload_invalid"))
    from_version = data["from_version"]
    to_version = data["to_version"]
    observed_on = data["observed_on"]
    read_timeout = data["read_timeout_seconds"]
    if (
        type(from_version) is not str
        or type(to_version) is not str
        or type(observed_on) is not str
        or type(read_timeout) not in {int, float}
        or not math.isfinite(read_timeout)
        or not 0 < read_timeout <= _MAX_READ_TIMEOUT_SECONDS
    ):
        raise _ProbeExecutorError(_child_failure("child_payload_invalid"))
    try:
        validate_exact_version(from_version)
        validate_exact_version(to_version)
        _validate_upgrade_order(from_version, to_version)
        _parse_observed_on(observed_on)
    except (ValueError, argparse.ArgumentTypeError):
        raise _ProbeExecutorError(_child_failure("child_payload_invalid")) from None
    return _ProbeRequest(
        from_version=from_version,
        to_version=to_version,
        observed_on=observed_on,
        read_timeout_seconds=float(read_timeout),
    )


def _parse_child_payload(payload: bytes) -> object:
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise _ProbeExecutorError(_child_failure("child_payload_invalid")) from None
    if type(data) is not dict or type(data.get("kind")) is not str:
        raise _ProbeExecutorError(_child_failure("child_payload_invalid"))
    kind = data["kind"]
    if kind == "report" and set(data) == {"kind", "report"}:
        return data["report"]
    if kind == "runtime_error" and set(data) == {"kind", "phase", "code", "diagnostic"}:
        phase = data["phase"]
        code = data["code"]
        diagnostic = data["diagnostic"]
        if (
            type(phase) is str
            and phase in _RUNTIME_PHASE_VALUES
            and type(code) is str
            and code in _RUNTIME_CODE_VALUES
            and type(diagnostic) is str
            and diagnostic in _STDERR_CATEGORY_VALUES
        ):
            raise _ProbeExecutorError(_runtime_failure(phase=phase, code=code, diagnostic=diagnostic))
    if kind == "error" and set(data) == {"kind", "reason"}:
        reason = data["reason"]
        if type(reason) is str and reason in _CHILD_ERROR_REASONS:
            raise _ProbeExecutorError(_child_failure(reason))
    raise _ProbeExecutorError(_child_failure("child_payload_invalid"))


def _child_failure(reason: str) -> dict[str, str]:
    if reason == "timeout":
        return {
            "code": "probe_execution_failed",
            "reason": "timeout",
            "remediation": "Retry with a bounded probe timeout after checking published server startup locally.",
        }
    if reason == "child_payload_invalid":
        return {
            "code": "probe_execution_failed",
            "reason": "child_payload_invalid",
            "remediation": "Retry with a runtime that emits one bounded canonical child result.",
        }
    return {
        "code": "probe_execution_failed",
        "reason": reason,
        "remediation": "Retry after checking published child startup and diagnostics locally.",
    }


def _runtime_failure(*, phase: str, code: str, diagnostic: str) -> dict[str, str]:
    return {
        "code": "probe_execution_failed",
        "phase": phase,
        "runtime_code": code,
        "diagnostic": diagnostic,
        "remediation": "Retry after checking PyPI visibility and published server diagnostics locally.",
    }


def _probe_child_main(encoded_request: str) -> int:
    try:
        request = _decode_probe_request(encoded_request)
        with tempfile.TemporaryDirectory(prefix="albumentationsx-mcp-upgrade-") as temporary:
            root = Path(temporary)
            report = asyncio.run(
                run_published_upgrade(
                    PublishedUpgradeConfig(
                        from_version=request.from_version,
                        to_version=request.to_version,
                        observed_on=request.observed_on,
                        allowed_root=root,
                        artifact_root=root / "artifacts",
                        read_timeout_seconds=request.read_timeout_seconds,
                    )
                )
            )
        envelope: dict[str, object] = {"kind": "report", "report": report}
    except BaseException as error:  # noqa: BLE001 - child emits only finite envelopes.
        runtime_error = _find_nested_exception(error, PublishedUpgradeRuntimeError)
        if runtime_error is not None:
            envelope = {
                "kind": "runtime_error",
                "phase": runtime_error.phase.value,
                "code": runtime_error.code.value,
                "diagnostic": runtime_error.diagnostic.value,
            }
        elif isinstance(error, _ProbeExecutorError):
            envelope = {"kind": "error", "reason": "child_payload_invalid"}
        else:
            envelope = {"kind": "error", "reason": "operational_error"}
    return _write_child_envelope(envelope)


def _write_child_envelope(envelope: dict[str, object]) -> int:
    try:
        payload = json.dumps(
            envelope,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError):
        payload = b'{"kind":"error","reason":"child_payload_invalid"}'
    if len(payload) > _MAX_CHILD_PAYLOAD_BYTES:
        payload = b'{"kind":"error","reason":"child_payload_invalid"}'
    try:
        sys.stdout.buffer.write(payload)
        sys.stdout.buffer.flush()
    except (OSError, ValueError):
        return 1
    return 0


# Failure normalization


def _nested_exceptions(error: BaseException) -> tuple[BaseException, ...]:
    nested = getattr(error, "exceptions", ())
    if not isinstance(nested, tuple):
        return ()
    return tuple(item for item in nested if isinstance(item, BaseException))


def _find_nested_exception(error: BaseException, exception_type: type[_ExceptionT]) -> _ExceptionT | None:
    if isinstance(error, exception_type):
        return error
    for nested in _nested_exceptions(error):
        found = _find_nested_exception(nested, exception_type)
        if found is not None:
            return found
    return None


def _raise_control_flow(error: BaseException) -> None:
    for exception_type in (asyncio.CancelledError, KeyboardInterrupt, SystemExit):
        control_flow = _find_nested_exception(error, exception_type)
        if control_flow is not None:
            raise control_flow from None


def _contains_timeout_error(error: BaseException) -> bool:
    timeout_types = (TimeoutError,) if asyncio.TimeoutError is TimeoutError else (TimeoutError, asyncio.TimeoutError)
    return any(_find_nested_exception(error, exception_type) is not None for exception_type in timeout_types)


def _probe_failure(error: BaseException) -> dict[str, str]:
    _raise_control_flow(error)
    executor_error = _find_nested_exception(error, _ProbeExecutorError)
    if executor_error is not None:
        return dict(executor_error.failure)
    runtime_error = _find_nested_exception(error, PublishedUpgradeRuntimeError)
    if runtime_error is not None:
        return _runtime_failure(
            phase=runtime_error.phase.value,
            code=runtime_error.code.value,
            diagnostic=runtime_error.diagnostic.value,
        )
    if _contains_timeout_error(error):
        return {
            "code": "probe_execution_failed",
            "reason": "timeout",
            "remediation": "Retry with a bounded probe timeout after checking published server startup locally.",
        }
    if isinstance(error, Exception):
        return {
            "code": "probe_execution_failed",
            "reason": "operational_error",
            "remediation": "Retry after checking PyPI visibility and published server diagnostics locally.",
        }
    raise error


def _emit_failure(
    context: _FailureContext,
    *,
    failures: list[dict[str, str]],
) -> None:
    report = {
        "schema_version": _SCHEMA_VERSION,
        "package": PACKAGE,
        "from_version": context.from_version,
        "to_version": context.to_version,
        "observed_on": context.observed_on.isoformat(),
        "status": "fail",
        "failures": failures,
    }
    sys.stderr.write(_serialize_json(report))


def _serialize_json(value: object) -> str:
    return json.dumps(value, allow_nan=False, indent=2, sort_keys=True) + "\n"


def _serialize_report(report: UpgradeProofReport) -> str:
    return serialize_upgrade_proof_report(report)


# Durable atomic output


def _write_atomic(path: Path, content: str) -> None:
    if _supports_posix_dirfd_output():
        _write_atomic_posix(path, content)
    else:
        _write_atomic_fallback(path, content)


def _supports_posix_dirfd_output() -> bool:
    return (
        os.name == "posix"
        and bool(getattr(os, "O_DIRECTORY", 0))
        and bool(getattr(os, "O_NOFOLLOW", 0))
        and os.open in os.supports_dir_fd
        and os.link in os.supports_dir_fd
        and os.stat in os.supports_dir_fd
        and os.unlink in os.supports_dir_fd
    )


def _validated_output_parts(path: Path) -> tuple[str, tuple[str, ...]]:
    encoded = os.fspath(path)
    parts = path.parts
    if not encoded or len(encoded) > _MAX_OUTPUT_PATH_LENGTH or len(parts) > _MAX_OUTPUT_COMPONENTS or not parts:
        message = "output path shape is invalid"
        raise OSError(message)
    anchor = path.anchor
    relative_parts = parts[1:] if anchor else parts
    if not relative_parts or any(
        component in {"", ".", ".."} or len(component) > _MAX_OUTPUT_COMPONENT_LENGTH for component in relative_parts
    ):
        message = "output path shape is invalid"
        raise OSError(message)
    return anchor, tuple(relative_parts)


def _directory_open_flags() -> int:
    return os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)


def _open_output_parent_posix(path: Path) -> tuple[int, str]:
    anchor, parts = _validated_output_parts(path)
    current_fd = os.open(anchor or ".", _directory_open_flags())
    try:
        for component in parts[:-1]:
            next_fd = os.open(component, _directory_open_flags(), dir_fd=current_fd)
            os.close(current_fd)
            current_fd = next_fd
    except BaseException:
        os.close(current_fd)
        raise
    return current_fd, parts[-1]


def _regular_destination_at(parent_fd: int, filename: str) -> os.stat_result | None:
    try:
        result = os.stat(filename, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(result.st_mode):
        message = "output path must name a regular non-symlink file"
        raise OSError(message)
    return result


def _open_temporary_at(parent_fd: int) -> tuple[int, str]:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    for _attempt in range(_TEMP_FILE_ATTEMPTS):
        filename = f".published-upgrade-temp-{secrets.token_hex(12)}.tmp"
        try:
            return os.open(filename, flags, 0o600, dir_fd=parent_fd), filename
        except FileExistsError:
            continue
    message = "unable to allocate a unique output temporary file"
    raise OSError(message)


def _same_file_identity(left: os.stat_result, right: os.stat_result) -> bool:
    return (
        stat.S_ISREG(left.st_mode)
        and stat.S_ISREG(right.st_mode)
        and left.st_dev == right.st_dev
        and left.st_ino == right.st_ino
    )


def _require_same_file_identity(expected: os.stat_result, *observed: os.stat_result) -> None:
    if not all(_same_file_identity(expected, item) for item in observed):
        message = "output destination identity changed before replacement"
        raise OSError(message)


def _create_backup_at(parent_fd: int, destination_name: str, expected: os.stat_result) -> str:
    for _attempt in range(_TEMP_FILE_ATTEMPTS):
        backup_name = f".published-upgrade-backup-{secrets.token_hex(12)}.tmp"
        try:
            os.link(
                destination_name,
                backup_name,
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
                follow_symlinks=False,
            )
        except FileExistsError:
            continue
        try:
            current = os.stat(destination_name, dir_fd=parent_fd, follow_symlinks=False)
            backup = os.stat(backup_name, dir_fd=parent_fd, follow_symlinks=False)
            _require_same_file_identity(expected, current, backup)
        except BaseException:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(backup_name, dir_fd=parent_fd)
            raise
        return backup_name
    message = "unable to allocate a unique output backup file"
    raise OSError(message)


def _rollback_replacement_at(parent_fd: int, destination_name: str, backup_name: str | None) -> None:
    if backup_name is None:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(destination_name, dir_fd=parent_fd)
    else:
        os.replace(
            backup_name,
            destination_name,
            src_dir_fd=parent_fd,
            dst_dir_fd=parent_fd,
        )
    with contextlib.suppress(OSError):
        os.fsync(parent_fd)


def _write_atomic_posix(path: Path, content: str) -> None:
    parent_fd, destination_name = _open_output_parent_posix(path)
    temporary_name: str | None = None
    temporary_fd: int | None = None
    backup_name: str | None = None
    try:
        previous = _regular_destination_at(parent_fd, destination_name)
        temporary_fd, temporary_name = _open_temporary_at(parent_fd)
        with os.fdopen(temporary_fd, mode="w", encoding="utf-8", newline="\n") as handle:
            temporary_fd = None
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if previous is None:
            if _regular_destination_at(parent_fd, destination_name) is not None:
                message = "output destination identity changed before replacement"
                raise OSError(message)
        else:
            backup_name = _create_backup_at(parent_fd, destination_name, previous)
            os.fsync(parent_fd)
        os.replace(
            temporary_name,
            destination_name,
            src_dir_fd=parent_fd,
            dst_dir_fd=parent_fd,
        )
        temporary_name = None
        try:
            os.fsync(parent_fd)
        except OSError:
            _rollback_replacement_at(parent_fd, destination_name, backup_name)
            backup_name = None
            raise
        if backup_name is not None:
            # The report is committed; backup unlink durability is cleanup, not report durability.
            with contextlib.suppress(OSError):
                os.unlink(backup_name, dir_fd=parent_fd)
            backup_name = None
    finally:
        if temporary_fd is not None:
            os.close(temporary_fd)
        if temporary_name is not None:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(temporary_name, dir_fd=parent_fd)
        if backup_name is not None:
            with contextlib.suppress(OSError):
                os.unlink(backup_name, dir_fd=parent_fd)
        os.close(parent_fd)


def _validate_fallback_output_path(path: Path) -> os.stat_result | None:
    """Validate without following links where dirfd/O_NOFOLLOW APIs are unavailable."""
    anchor, parts = _validated_output_parts(path)
    current = Path(anchor) if anchor else Path.cwd()
    for component in parts[:-1]:
        current /= component
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            message = "output parent directory must already exist"
            raise OSError(message) from None
        if not stat.S_ISDIR(mode) or stat.S_ISLNK(mode):
            message = "output parent must be a regular non-symlink directory"
            raise OSError(message)
    destination = current / parts[-1]
    try:
        result = destination.lstat()
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(result.st_mode):
        message = "output path must name a regular non-symlink file"
        raise OSError(message)
    return result


def _fsync_directory(path: Path, *, best_effort: bool = False) -> None:
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    except OSError:
        if best_effort or os.name == "nt":
            return
        raise
    try:
        os.fsync(descriptor)
    except OSError:
        if not best_effort:
            raise
    finally:
        os.close(descriptor)


def _create_fallback_backup(path: Path, expected: os.stat_result) -> Path:
    for _attempt in range(_TEMP_FILE_ATTEMPTS):
        backup = path.parent / f".published-upgrade-backup-{secrets.token_hex(12)}.tmp"
        try:
            os.link(path, backup, follow_symlinks=False)
        except FileExistsError:
            continue
        try:
            current = path.lstat()
            backup_stat = backup.lstat()
            _require_same_file_identity(expected, current, backup_stat)
        except BaseException:
            backup.unlink(missing_ok=True)
            raise
        return backup
    message = "unable to allocate a unique output backup file"
    raise OSError(message)


def _rollback_fallback_replacement(path: Path, backup: Path | None) -> None:
    if backup is None:
        path.unlink(missing_ok=True)
    else:
        os.replace(backup, path)  # noqa: PTH105 - explicit rollback primitive.
    _fsync_directory(path.parent, best_effort=True)


def _write_atomic_fallback(path: Path, content: str) -> None:
    """Use a same-directory atomic replace on platforms without secure dirfd traversal."""
    previous = _validate_fallback_output_path(path)
    temporary_path: Path | None = None
    backup_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        current = _validate_fallback_output_path(path)
        if previous is None:
            if current is not None:
                message = "output destination identity changed before replacement"
                raise OSError(message)
        else:
            if current is None or not _same_file_identity(previous, current):
                message = "output destination identity changed before replacement"
                raise OSError(message)
            backup_path = _create_fallback_backup(path, previous)
            _fsync_directory(path.parent)
        os.replace(temporary_path, path)  # noqa: PTH105 - explicit atomic primitive is injected in tests.
        temporary_path = None
        try:
            _fsync_directory(path.parent)
        except OSError:
            _rollback_fallback_replacement(path, backup_path)
            backup_path = None
            raise
        if backup_path is not None:
            # The report is committed; backup unlink durability is cleanup, not report durability.
            with contextlib.suppress(OSError):
                backup_path.unlink()
            backup_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        if backup_path is not None:
            with contextlib.suppress(OSError):
                backup_path.unlink(missing_ok=True)


if __name__ == "__main__":
    if len(sys.argv) == _CHILD_ARG_COUNT and sys.argv[1] == _CHILD_MODE:
        raise SystemExit(_probe_child_main(sys.argv[2]))
    raise SystemExit(main())
