"""Prove compatibility between two exact published AlbumentationsX MCP versions."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import re
import stat
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Final, Protocol, TypeVar

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcp.types.version import LATEST_MODERN_VERSION

from albumentationsx_mcp.upgrade_proof import UpgradeProofReport
from scripts.check_published_package_smoke import check_pypi_version
from scripts.published_upgrade_runtime import (
    PACKAGE,
    PublishedUpgradeConfig,
    PublishedUpgradeRuntimeError,
    build_attested_uvx_server_command,
    run_published_upgrade,
)

_SCHEMA_VERSION: Final = "albumentationsx-mcp/published-upgrade-proof/v1"
_EXACT_VERSION: Final = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\Z")
_MAX_VERSION_LENGTH: Final = 128
_MAX_RETRIES: Final = 10
_MAX_RETRY_DELAY_SECONDS: Final = 300.0
_MAX_PYPI_TIMEOUT_SECONDS: Final = 120.0
_MAX_READ_TIMEOUT_SECONDS: Final = 600.0
_MAX_PROBE_TIMEOUT_SECONDS: Final = 3600.0
_MAX_SERIALIZED_REPORT_BYTES: Final = 1024 * 1024


class _PyPIVersionCheck(Protocol):
    def __call__(self, *, package: str, version: str, timeout_seconds: float) -> str | None: ...


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
        failures = [
            {
                "code": "pypi_version_unavailable",
                "scope": "from_version" if version == args.from_version else "to_version",
                "remediation": "Retry after the exact release is visible on the public PyPI version endpoint.",
            }
            for version in unavailable_versions
        ]
        _emit_failure(context, failures=failures)
        return False
    return True


def _collect_upgrade_report(
    args: argparse.Namespace,
    context: _FailureContext,
) -> UpgradeProofReport | None:
    try:
        with tempfile.TemporaryDirectory(prefix="albumentationsx-mcp-upgrade-") as temporary:
            root = Path(temporary)
            report = _run_probe(
                PublishedUpgradeConfig(
                    from_version=args.from_version,
                    to_version=args.to_version,
                    observed_on=context.observed_on.isoformat(),
                    allowed_root=root,
                    artifact_root=root / "artifacts",
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
    report: UpgradeProofReport,
    context: _FailureContext,
) -> tuple[str, str] | None:
    try:
        content = _serialize_report(report)
        status = _validated_report_status(report)
    except (KeyError, TypeError, ValueError):
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
    return content, status


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
) -> tuple[str, ...]:
    unavailable: list[str] = []
    for version in dict.fromkeys(config.versions):
        for attempt in range(config.retries):
            error = check_version(package=PACKAGE, version=version, timeout_seconds=config.timeout_seconds)
            if error is None:
                break
            if attempt + 1 < config.retries:
                sleep(config.delay_seconds)
        else:
            unavailable.append(version)
    return tuple(unavailable)


async def _bounded_probe(config: PublishedUpgradeConfig, timeout_seconds: float) -> UpgradeProofReport:
    return await asyncio.wait_for(run_published_upgrade(config), timeout=timeout_seconds)


def _run_probe(config: PublishedUpgradeConfig, timeout_seconds: float) -> UpgradeProofReport:
    return asyncio.run(_bounded_probe(config, timeout_seconds))


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
            raise control_flow


def _probe_failure(error: BaseException) -> dict[str, str]:
    _raise_control_flow(error)
    runtime_error = _find_nested_exception(error, PublishedUpgradeRuntimeError)
    if runtime_error is not None:
        return {
            "code": "probe_execution_failed",
            "phase": runtime_error.phase.value,
            "runtime_code": runtime_error.code.value,
            "diagnostic": runtime_error.diagnostic.value,
            "remediation": "Retry after checking PyPI visibility and published server diagnostics locally.",
        }
    if _find_nested_exception(error, TimeoutError) is not None:
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
    content = _serialize_json(report)
    if len(content.encode("utf-8")) > _MAX_SERIALIZED_REPORT_BYTES:
        message = "published upgrade report exceeds the output bound"
        raise ValueError(message)
    return content


def _validated_report_status(report: UpgradeProofReport) -> str:
    status = report["status"]
    if status not in {"pass", "fail"}:
        message = "published upgrade report has an invalid status"
        raise ValueError(message)
    return status


def _validate_output_path(path: Path) -> None:
    if not path.name or path.name in {".", ".."}:
        message = "output path must name a regular file"
        raise OSError(message)
    if path.is_symlink() or path.parent.is_symlink():
        message = "output path must not be a symlink"
        raise OSError(message)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.is_symlink() or not path.parent.is_dir():
        message = "output parent must be a regular directory"
        raise OSError(message)
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return
    if not stat.S_ISREG(mode):
        message = "output path must name a regular file"
        raise OSError(message)


def _write_atomic(path: Path, content: str) -> None:
    _validate_output_path(path)
    temporary_path: Path | None = None
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
        os.replace(temporary_path, path)  # noqa: PTH105 - explicit atomic primitive is injected in tests.
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
