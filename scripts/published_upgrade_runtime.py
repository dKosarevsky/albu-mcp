"""Runtime adapter for published AlbumentationsX MCP upgrade probes."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import os
import re
import select
import shutil
import stat
import tempfile
import threading
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from contextlib import AbstractAsyncContextManager, asynccontextmanager, nullcontext, suppress
from dataclasses import dataclass
from enum import Enum
from io import BytesIO
from pathlib import Path
from typing import Any, Literal, Protocol, TextIO, TypeAlias, TypeVar

from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import BlobResourceContents
from mcp.types.version import LATEST_HANDSHAKE_VERSION, LATEST_MODERN_VERSION
from PIL import Image
from typing_extensions import Self

from albumentationsx_mcp.upgrade_proof import (
    ArtifactContinuity,
    ProtocolObservation,
    PublicSurface,
    UpgradeProofReport,
    build_upgrade_proof_report,
)

PACKAGE = "albumentationsx-mcp"
ConnectionMode: TypeAlias = Literal["legacy", "auto"]
_RUNTIME_ERROR_MESSAGE = "Published upgrade probe failed."
_MAX_STDERR_INSPECT_BYTES = 16 * 1024
_STDERR_DRAIN_TIMEOUT_SECONDS = 1.0
_ATTESTATION_STDERR_MARKER = b"ALBU_MCP_ATTESTATION_FAILED"
_MAX_PNG_DECODED_BYTES = 8 * 1024 * 1024
_MAX_PNG_ENCODED_BYTES = ((_MAX_PNG_DECODED_BYTES + 2) // 3) * 4
_MAX_PNG_WIDTH = 4096
_MAX_PNG_HEIGHT = 4096
_MAX_PNG_PIXELS = 16 * 1024 * 1024
_RUN_ID_PATTERN = re.compile(r"[0-9a-f]{32}\Z")
_LOWER_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")


def _marker_prefix_table(marker: bytes) -> tuple[int, ...]:
    table = [0] * len(marker)
    prefix_length = 0
    for index in range(1, len(marker)):
        while prefix_length and marker[index] != marker[prefix_length]:
            prefix_length = table[prefix_length - 1]
        if marker[index] == marker[prefix_length]:
            prefix_length += 1
            table[index] = prefix_length
    return tuple(table)


_ATTESTATION_MARKER_PREFIXES = _marker_prefix_table(_ATTESTATION_STDERR_MARKER)

PUBLISHED_SERVER_BOOTSTRAP = """\
from importlib.metadata import version
import sys

expected_version = sys.argv[1]
try:
    observed_version = version("albumentationsx-mcp")
except Exception:
    print("ALBU_MCP_ATTESTATION_FAILED", file=sys.stderr)
    raise SystemExit(86) from None
if observed_version != expected_version:
    print("ALBU_MCP_ATTESTATION_FAILED", file=sys.stderr)
    raise SystemExit(86)

import albumentationsx_mcp.cli

sys.argv = ["albumentationsx-mcp", *sys.argv[2:]]
albumentationsx_mcp.cli.main()
"""

_SAFE_CHILD_ENVIRONMENT = frozenset(
    {
        "ALL_PROXY",
        "CURL_CA_BUNDLE",
        "HOME",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "LANG",
        "LANGUAGE",
        "LC_ADDRESS",
        "LC_ALL",
        "LC_COLLATE",
        "LC_CTYPE",
        "LC_IDENTIFICATION",
        "LC_MEASUREMENT",
        "LC_MESSAGES",
        "LC_MONETARY",
        "LC_NAME",
        "LC_NUMERIC",
        "LC_PAPER",
        "LC_TELEPHONE",
        "LC_TIME",
        "LOGNAME",
        "NO_PROXY",
        "PATH",
        "REQUESTS_CA_BUNDLE",
        "SHELL",
        "SSL_CERT_DIR",
        "SSL_CERT_FILE",
        "TEMP",
        "TERM",
        "TMP",
        "TMPDIR",
        "USER",
        "all_proxy",
        "http_proxy",
        "https_proxy",
        "no_proxy",
    }
)
_MAX_SURFACE_PAGES = 32
_MAX_SURFACE_IDENTIFIERS = 4096
_MAX_SURFACE_IDENTIFIER_LENGTH = 4096
_MAX_SURFACE_CURSOR_LENGTH = 1024
_SURFACE_COLLECTION_FIELDS = {
    "tools": "name",
    "resources": "uri",
    "resource_templates": "uri_template",
    "prompts": "name",
}


class RuntimePhase(str, Enum):
    """Finite runtime phases safe to expose in automation logs."""

    STARTUP = "startup"
    NEGOTIATION = "negotiation"
    REQUEST = "request"
    CONTEXT_EXIT = "context_exit"
    FILESYSTEM = "filesystem"


class RuntimeCode(str, Enum):
    """Finite runtime failure codes safe to expose in automation logs."""

    CLIENT_CONNECT_FAILED = "client_connect_failed"
    CHILD_START_FAILED = "child_start_failed"
    DISTRIBUTION_ATTESTATION_FAILED = "distribution_attestation_failed"
    NEGOTIATION_FAILED = "negotiation_failed"
    REQUEST_FAILED = "request_failed"
    TIMEOUT = "timeout"
    CONTEXT_EXIT_FAILED = "context_exit_failed"
    RESOURCE_CONTENT_COUNT_INVALID = "resource_content_count_invalid"
    RESOURCE_CONTENT_TYPE_INVALID = "resource_content_type_invalid"
    RESOURCE_URI_MISMATCH = "resource_uri_mismatch"
    RESOURCE_MIME_INVALID = "resource_mime_invalid"
    RESOURCE_BASE64_INVALID = "resource_base64_invalid"
    RESOURCE_ENCODED_TOO_LARGE = "resource_encoded_too_large"
    RESOURCE_DECODED_TOO_LARGE = "resource_decoded_too_large"
    RESOURCE_PNG_INVALID = "resource_png_invalid"
    RESOURCE_DIMENSIONS_INVALID = "resource_dimensions_invalid"
    TOOL_RESULT_INVALID = "tool_result_invalid"
    MANIFEST_INVALID = "manifest_invalid"
    MANIFEST_RUN_ID_MISMATCH = "manifest_run_id_mismatch"
    CONTACT_SHEET_COUNT_INVALID = "contact_sheet_count_invalid"
    CONTACT_SHEET_ARTIFACT_INVALID = "contact_sheet_artifact_invalid"
    CONTACT_SHEET_URI_MISMATCH = "contact_sheet_uri_mismatch"
    ARTIFACT_SIZE_MISMATCH = "artifact_size_mismatch"
    ARTIFACT_DIGEST_MISMATCH = "artifact_digest_mismatch"
    ARTIFACT_SEED_DIGEST_MISMATCH = "artifact_seed_digest_mismatch"
    PAGINATION_CURSOR_REPEATED = "pagination_cursor_repeated"
    PAGINATION_PAGE_LIMIT = "pagination_page_limit"
    PAGINATION_IDENTIFIER_LIMIT = "pagination_identifier_limit"
    PAGINATION_PAGE_INVALID = "pagination_page_invalid"
    PAGINATION_ITEM_INVALID = "pagination_item_invalid"
    ALLOWED_ROOT_INVALID = "allowed_root_invalid"
    FIXTURE_CREATE_FAILED = "fixture_create_failed"
    FIXTURE_CLEANUP_FAILED = "fixture_cleanup_failed"


class StderrCategory(str, Enum):
    """Finite diagnostic categories derived without retaining child stderr."""

    NONE = "none"
    ATTESTATION = "attestation"
    OTHER = "other"
    TRUNCATED = "truncated"


class PublishedUpgradeRuntimeError(RuntimeError):
    """Privacy-safe failure raised by published upgrade orchestration."""

    def __init__(
        self,
        *,
        phase: RuntimePhase,
        code: RuntimeCode,
        diagnostic: StderrCategory = StderrCategory.NONE,
    ) -> None:
        self.phase = phase
        self.code = code
        self.diagnostic = diagnostic
        super().__init__(_RUNTIME_ERROR_MESSAGE)

    def to_dict(self) -> dict[str, str]:
        """Return the fixed bounded serialization intended for automation."""
        return {
            "phase": self.phase.value,
            "code": self.code.value,
            "diagnostic": self.diagnostic.value,
            "message": _RUNTIME_ERROR_MESSAGE,
        }


class _StderrSink(Protocol):
    category: StderrCategory

    @property
    def stream(self) -> TextIO: ...

    def __enter__(self) -> Self: ...

    def __exit__(self, *_args: object) -> None: ...

    def finish_and_classify(self) -> StderrCategory: ...


class _DevnullStderrSink:
    """Discard child stderr on platforms where select cannot monitor pipes."""

    def __init__(self) -> None:
        self.category = StderrCategory.NONE
        self._stream: TextIO | None = None

    @property
    def stream(self) -> TextIO:
        if self._stream is None:
            message = "stderr sink must be entered before use"
            raise RuntimeError(message)
        return self._stream

    def __enter__(self) -> Self:
        self._stream = Path(os.devnull).open("w", encoding="utf-8")
        return self

    def __exit__(self, *_args: object) -> None:
        self.finish_and_classify()

    def finish_and_classify(self) -> StderrCategory:
        if self._stream is not None and not self._stream.closed:
            self._stream.close()
        return self.category


class _BoundedStderrSink:
    """Drain child stderr without retaining raw bytes."""

    def __init__(self) -> None:
        self.category = StderrCategory.NONE
        self.inspected_bytes = 0
        self._stream: TextIO | None = None
        self._thread: threading.Thread | None = None
        self._read_fd: int | None = None
        self._wake_read_fd: int | None = None
        self._wake_write_fd: int | None = None
        self._marker_prefix_length = 0
        self._finish_lock = threading.Lock()
        self._finished = False

    @property
    def stream(self) -> TextIO:
        """Return the writable stream connected to the bounded drain."""
        if self._stream is None:
            message = "stderr sink must be entered before use"
            raise RuntimeError(message)
        return self._stream

    def __enter__(self) -> Self:
        read_fd, write_fd = os.pipe()
        wake_read_fd, wake_write_fd = os.pipe()
        self._read_fd = read_fd
        self._wake_read_fd = wake_read_fd
        self._wake_write_fd = wake_write_fd
        self._stream = os.fdopen(write_fd, "w", encoding="utf-8")
        self._thread = threading.Thread(
            target=self._drain,
            args=(read_fd, wake_read_fd),
            daemon=False,
        )
        self._thread.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self.finish()

    def finish(self) -> None:
        """Close the parent writer and wait for the bounded drain to finish."""
        with self._finish_lock:
            if self._finished:
                return
            if self._stream is not None and not self._stream.closed:
                self._stream.close()
            if self._thread is not None:
                self._thread.join(timeout=_STDERR_DRAIN_TIMEOUT_SECONDS)
                if self._thread.is_alive():
                    if self.category is not StderrCategory.ATTESTATION:
                        self.category = StderrCategory.TRUNCATED
                    self._wake_reader()
                    self._thread.join()
            if self._wake_write_fd is not None:
                with suppress(OSError):
                    os.close(self._wake_write_fd)
            self._thread = None
            self._read_fd = None
            self._wake_read_fd = None
            self._wake_write_fd = None
            self._finished = True

    def finish_and_classify(self) -> StderrCategory:
        """Finish draining stderr and return only its bounded category."""
        self.finish()
        return self.category

    def _wake_reader(self) -> None:
        if self._wake_write_fd is not None:
            with suppress(OSError):
                os.write(self._wake_write_fd, b"\0")

    def _drain(self, read_fd: int, wake_read_fd: int) -> None:
        try:
            while True:
                ready, _, _ = select.select((read_fd, wake_read_fd), (), ())
                if wake_read_fd in ready:
                    return
                chunk = os.read(read_fd, 4096)
                if not chunk:
                    return
                self._inspect_chunk(chunk)
        finally:
            with suppress(OSError):
                os.close(read_fd)
            with suppress(OSError):
                os.close(wake_read_fd)

    def _inspect_chunk(self, chunk: bytes) -> None:
        remaining = max(0, _MAX_STDERR_INSPECT_BYTES - self.inspected_bytes)
        sample = chunk[:remaining]
        self.inspected_bytes += len(sample)
        for byte in sample:
            while self._marker_prefix_length and byte != _ATTESTATION_STDERR_MARKER[self._marker_prefix_length]:
                self._marker_prefix_length = _ATTESTATION_MARKER_PREFIXES[self._marker_prefix_length - 1]
            if byte == _ATTESTATION_STDERR_MARKER[self._marker_prefix_length]:
                self._marker_prefix_length += 1
                if self._marker_prefix_length == len(_ATTESTATION_STDERR_MARKER):
                    self.category = StderrCategory.ATTESTATION
                    self._marker_prefix_length = _ATTESTATION_MARKER_PREFIXES[self._marker_prefix_length - 1]
        if sample.strip() and self.category is StderrCategory.NONE:
            self.category = StderrCategory.OTHER
        if len(chunk) > remaining and self.category is not StderrCategory.ATTESTATION:
            self.category = StderrCategory.TRUNCATED


def _stderr_sink() -> _StderrSink:
    return _BoundedStderrSink() if os.name == "posix" else _DevnullStderrSink()


@dataclass(frozen=True)
class PublishedUpgradeConfig:
    """Inputs shared across the three published-server observations."""

    from_version: str
    to_version: str
    observed_on: str
    allowed_root: Path
    artifact_root: Path
    read_timeout_seconds: float


@dataclass(frozen=True)
class ServerClientRequest:
    """Connection details for one isolated published server process."""

    version: str
    mode: ConnectionMode
    allowed_root: Path
    artifact_root: Path
    read_timeout_seconds: float


class ClientFactory(Protocol):
    """Create connected clients for injectable upgrade orchestration."""

    def __call__(self, request: ServerClientRequest, /) -> AbstractAsyncContextManager[Client]:
        """Return an async context manager yielding a connected MCP client."""
        raise NotImplementedError


@dataclass(frozen=True)
class _ArtifactSeed:
    run_id: str
    contact_sheet_uri: str
    contact_sheet_sha256: str


@dataclass(frozen=True)
class _ContactSheetArtifact:
    uri: str
    mime_type: str
    size_bytes: int
    sha256: str


def build_uvx_server_command(version: str) -> list[str]:
    """Build an exact-version uvx server command."""
    return [
        "uvx",
        "--from",
        f"{PACKAGE}=={version}",
        "--refresh-package",
        PACKAGE,
        PACKAGE,
    ]


def build_attested_uvx_server_command(version: str) -> list[str]:
    """Build a same-process uvx command that attests the installed distribution."""
    base_command = build_uvx_server_command(version)
    return [
        *base_command[:-1],
        "--isolated",
        "--no-config",
        "--no-env-file",
        "--no-sources",
        "python",
        "-I",
        "-c",
        PUBLISHED_SERVER_BOOTSTRAP,
        version,
    ]


def clean_subprocess_environment(environment: Mapping[str, str] | None = None) -> dict[str, str]:
    """Select only bounded runtime, network, locale, and certificate settings."""
    source = os.environ if environment is None else environment
    return {name: value for name, value in source.items() if name in _SAFE_CHILD_ENVIRONMENT}


def _nested_exceptions(error: BaseException) -> tuple[BaseException, ...]:
    nested = getattr(error, "exceptions", ())
    if not isinstance(nested, tuple):
        return ()
    return tuple(item for item in nested if isinstance(item, BaseException))


_ExceptionT = TypeVar("_ExceptionT", bound=BaseException)


def _find_nested_exception(error: BaseException, exception_type: type[_ExceptionT]) -> _ExceptionT | None:
    if isinstance(error, exception_type):
        return error
    for item in _nested_exceptions(error):
        found = _find_nested_exception(item, exception_type)
        if found is not None:
            return found
    return None


_ErrorCandidate: TypeAlias = tuple[BaseException | None, RuntimePhase, RuntimeCode, StderrCategory]


def _select_runtime_error(*candidates: _ErrorCandidate) -> BaseException | None:
    """Select cancellation, interrupts, exits, normalized errors, then ordinary errors."""
    for control_flow_type in (asyncio.CancelledError, KeyboardInterrupt, SystemExit, GeneratorExit):
        for error, _phase, _code, _diagnostic in candidates:
            if error is None:
                continue
            control_flow = _find_nested_exception(error, control_flow_type)
            if control_flow is not None:
                return control_flow

    for error, _phase, _code, _diagnostic in candidates:
        if error is None:
            continue
        normalized = _find_nested_exception(error, PublishedUpgradeRuntimeError)
        if normalized is not None:
            return normalized

    for error, phase, code, diagnostic in candidates:
        if error is not None:
            normalized_code = RuntimeCode.TIMEOUT if _find_nested_exception(error, TimeoutError) is not None else code
            return PublishedUpgradeRuntimeError(
                phase=phase,
                code=normalized_code,
                diagnostic=diagnostic,
            )
    return None


def _normalize_runtime_error(
    error: BaseException,
    *,
    phase: RuntimePhase,
    code: RuntimeCode,
    diagnostic: StderrCategory = StderrCategory.NONE,
) -> BaseException:
    selected = _select_runtime_error((error, phase, code, diagnostic))
    if selected is None:
        message = "runtime normalization requires an error"
        raise RuntimeError(message)
    return selected


_ConnectFailure: TypeAlias = tuple[RuntimePhase, RuntimeCode]
_ClientManagerFactory: TypeAlias = Callable[[], AbstractAsyncContextManager[Client]]
_DEFAULT_CONNECT_FAILURE = (RuntimePhase.STARTUP, RuntimeCode.CLIENT_CONNECT_FAILED)


@asynccontextmanager
async def _connected_client(
    manager_factory: _ClientManagerFactory,
    *,
    connect_failure: Callable[[], _ConnectFailure] | None = None,
    diagnostic: Callable[[], StderrCategory] | None = None,
) -> AsyncIterator[Client]:
    """Classify one client lifecycle without exposing underlying exceptions."""
    connected = False
    body_error: BaseException | None = None
    caught_error: BaseException | None = None
    try:
        async with manager_factory() as client:
            connected = True
            try:
                yield client
            except BaseException as exc:
                body_error = exc
                raise
    except BaseException as exc:  # noqa: BLE001 - lifecycle boundaries may raise base exception groups.
        caught_error = exc

    if body_error is None and caught_error is None:
        return

    stderr_category = diagnostic() if diagnostic is not None else StderrCategory.NONE
    if connected:
        caught_phase, caught_code = (
            (RuntimePhase.REQUEST, RuntimeCode.REQUEST_FAILED)
            if caught_error is body_error
            else (RuntimePhase.CONTEXT_EXIT, RuntimeCode.CONTEXT_EXIT_FAILED)
        )
    else:
        caught_phase, caught_code = _DEFAULT_CONNECT_FAILURE if connect_failure is None else connect_failure()
    selected = _select_runtime_error(
        (body_error, RuntimePhase.REQUEST, RuntimeCode.REQUEST_FAILED, stderr_category),
        (caught_error, caught_phase, caught_code, stderr_category),
    )
    if selected is not None:
        raise selected from None


@asynccontextmanager
async def open_published_client(request: ServerClientRequest) -> AsyncIterator[Client]:
    """Start one pinned published server and yield its connected client."""
    command = build_attested_uvx_server_command(request.version)
    params = StdioServerParameters(
        command=command[0],
        args=[
            *command[1:],
            "--allowed-root",
            str(request.allowed_root),
            "--artifact-root",
            str(request.artifact_root),
            "--capability-profile",
            "full",
        ],
        cwd=str(request.allowed_root),
        env=clean_subprocess_environment(),
    )
    with _stderr_sink() as stderr_sink:
        transport_started = False

        @asynccontextmanager
        async def connect() -> AsyncIterator[Client]:
            nonlocal transport_started
            async with stdio_client(params, errlog=stderr_sink.stream) as streams:
                transport_started = True
                async with Client(
                    nullcontext(streams),
                    mode=request.mode,
                    read_timeout_seconds=request.read_timeout_seconds,
                ) as client:
                    yield client

        def classify_connect_failure() -> _ConnectFailure:
            if stderr_sink.category is StderrCategory.ATTESTATION:
                return RuntimePhase.STARTUP, RuntimeCode.DISTRIBUTION_ATTESTATION_FAILED
            if not transport_started:
                return RuntimePhase.STARTUP, RuntimeCode.CHILD_START_FAILED
            return RuntimePhase.NEGOTIATION, RuntimeCode.NEGOTIATION_FAILED

        async with _connected_client(
            connect,
            connect_failure=classify_connect_failure,
            diagnostic=stderr_sink.finish_and_classify,
        ) as client:
            yield client


async def run_published_upgrade(
    config: PublishedUpgradeConfig,
    *,
    client_factory: ClientFactory = open_published_client,
) -> UpgradeProofReport:
    """Probe the legacy-to-modern upgrade matrix and artifact continuity."""
    fixture_root, fixture_path = _create_fixture_workspace(config.allowed_root)
    report: UpgradeProofReport | None = None
    probe_error: BaseException | None = None
    try:
        from_request = _client_request(
            config,
            version=config.from_version,
            mode="legacy",
            allowed_root=fixture_root,
        )
        async with _connected_client(
            lambda: client_factory(from_request),
        ) as client:
            from_surface = await _snapshot_surface(client)
            from_legacy = _observation(
                client,
                from_request,
                evidence_mode="legacy",
                expected_protocol=LATEST_HANDSHAKE_VERSION,
                surface=from_surface,
            )
            seed = await _render_seed(client, fixture_path)

        to_legacy_request = _client_request(
            config,
            version=config.to_version,
            mode="legacy",
            allowed_root=fixture_root,
        )
        async with _connected_client(
            lambda: client_factory(to_legacy_request),
        ) as client:
            to_legacy_surface = await _snapshot_surface(client)
            to_legacy = _observation(
                client,
                to_legacy_request,
                evidence_mode="legacy",
                expected_protocol=LATEST_HANDSHAKE_VERSION,
                surface=to_legacy_surface,
            )

        to_modern_request = _client_request(
            config,
            version=config.to_version,
            mode="auto",
            allowed_root=fixture_root,
        )
        async with _connected_client(
            lambda: client_factory(to_modern_request),
        ) as client:
            to_modern_surface = await _snapshot_surface(client)
            to_modern = _observation(
                client,
                to_modern_request,
                evidence_mode=LATEST_MODERN_VERSION,
                expected_protocol=LATEST_MODERN_VERSION,
                surface=to_modern_surface,
            )
            artifact = await _read_old_artifact(client, seed)

        report = build_upgrade_proof_report(
            package=PACKAGE,
            from_version=config.from_version,
            to_version=config.to_version,
            observed_on=config.observed_on,
            from_legacy=from_legacy,
            to_legacy=to_legacy,
            to_modern=to_modern,
            artifact=artifact,
        )
    except BaseException as exc:  # noqa: BLE001 - cleanup must run after cancellation and exception groups.
        probe_error = exc

    cleanup_error: BaseException | None = None
    try:
        _remove_fixture_workspace(fixture_root)
    except BaseException as exc:  # noqa: BLE001 - cleanup failures are normalized at the outer boundary.
        cleanup_error = exc

    selected = _select_runtime_error(
        (probe_error, RuntimePhase.REQUEST, RuntimeCode.REQUEST_FAILED, StderrCategory.NONE),
        (cleanup_error, RuntimePhase.FILESYSTEM, RuntimeCode.FIXTURE_CLEANUP_FAILED, StderrCategory.NONE),
    )
    if selected is not None:
        raise selected from None
    if report is None:
        raise PublishedUpgradeRuntimeError(
            phase=RuntimePhase.REQUEST,
            code=RuntimeCode.REQUEST_FAILED,
        )
    return report


def _client_request(
    config: PublishedUpgradeConfig,
    *,
    version: str,
    mode: ConnectionMode,
    allowed_root: Path,
) -> ServerClientRequest:
    return ServerClientRequest(
        version=version,
        mode=mode,
        allowed_root=allowed_root,
        artifact_root=config.artifact_root,
        read_timeout_seconds=config.read_timeout_seconds,
    )


def _observation(
    client: Client,
    request: ServerClientRequest,
    *,
    evidence_mode: str,
    expected_protocol: str,
    surface: PublicSurface,
) -> ProtocolObservation:
    server_info = client.server_info
    return ProtocolObservation(
        server_version=request.version,
        observed_server_version=request.version,
        advertised_server_version=server_info.version if server_info is not None else "",
        client_mode=evidence_mode,
        expected_protocol=expected_protocol,
        negotiated_protocol=str(client.protocol_version),
        surface=surface,
    )


def _create_fixture_workspace(allowed_root: Path) -> tuple[Path, Path]:
    try:
        root_status = allowed_root.lstat()
    except OSError as exc:
        raise _normalize_runtime_error(
            exc,
            phase=RuntimePhase.FILESYSTEM,
            code=RuntimeCode.ALLOWED_ROOT_INVALID,
        ) from None
    if not allowed_root.is_absolute() or stat.S_ISLNK(root_status.st_mode) or not stat.S_ISDIR(root_status.st_mode):
        raise PublishedUpgradeRuntimeError(
            phase=RuntimePhase.FILESYSTEM,
            code=RuntimeCode.ALLOWED_ROOT_INVALID,
        )

    try:
        candidate = Path(tempfile.mkdtemp(prefix=".published-upgrade-", dir=allowed_root))
    except OSError as exc:
        raise _normalize_runtime_error(
            exc,
            phase=RuntimePhase.FILESYSTEM,
            code=RuntimeCode.FIXTURE_CREATE_FAILED,
        ) from None
    if candidate.parent != allowed_root or not candidate.name.startswith(".published-upgrade-"):
        raise PublishedUpgradeRuntimeError(
            phase=RuntimePhase.FILESYSTEM,
            code=RuntimeCode.FIXTURE_CREATE_FAILED,
        )

    fixture_root = candidate
    try:
        fixture_status = fixture_root.lstat()
    except OSError as exc:
        _discard_fixture_workspace(fixture_root)
        raise _normalize_runtime_error(
            exc,
            phase=RuntimePhase.FILESYSTEM,
            code=RuntimeCode.FIXTURE_CREATE_FAILED,
        ) from None
    if stat.S_ISLNK(fixture_status.st_mode) or not stat.S_ISDIR(fixture_status.st_mode):
        raise PublishedUpgradeRuntimeError(
            phase=RuntimePhase.FILESYSTEM,
            code=RuntimeCode.FIXTURE_CREATE_FAILED,
        )

    fixture_path = fixture_root / "fixture.png"
    try:
        with (
            fixture_path.open("xb") as fixture_file,
            Image.new(
                "RGB",
                (24, 24),
                (96, 128, 160),
            ) as fixture_image,
        ):
            fixture_image.save(fixture_file, format="PNG")
        file_status = fixture_path.lstat()
    except (OSError, ValueError) as exc:
        _discard_fixture_workspace(fixture_root)
        raise _normalize_runtime_error(
            exc,
            phase=RuntimePhase.FILESYSTEM,
            code=RuntimeCode.FIXTURE_CREATE_FAILED,
        ) from None
    if stat.S_ISLNK(file_status.st_mode) or not stat.S_ISREG(file_status.st_mode):
        _discard_fixture_workspace(fixture_root)
        raise PublishedUpgradeRuntimeError(
            phase=RuntimePhase.FILESYSTEM,
            code=RuntimeCode.FIXTURE_CREATE_FAILED,
        )
    return fixture_root, fixture_path


def _discard_fixture_workspace(fixture_root: Path) -> None:
    with suppress(PublishedUpgradeRuntimeError):
        _remove_fixture_workspace(fixture_root)


def _remove_fixture_workspace(fixture_root: Path) -> None:
    try:
        root_status = fixture_root.lstat()
    except OSError as exc:
        raise _normalize_runtime_error(
            exc,
            phase=RuntimePhase.FILESYSTEM,
            code=RuntimeCode.FIXTURE_CLEANUP_FAILED,
        ) from None
    if stat.S_ISLNK(root_status.st_mode) or not stat.S_ISDIR(root_status.st_mode):
        raise PublishedUpgradeRuntimeError(
            phase=RuntimePhase.FILESYSTEM,
            code=RuntimeCode.FIXTURE_CLEANUP_FAILED,
        )
    try:
        shutil.rmtree(fixture_root)
    except OSError as exc:
        raise _normalize_runtime_error(
            exc,
            phase=RuntimePhase.FILESYSTEM,
            code=RuntimeCode.FIXTURE_CLEANUP_FAILED,
        ) from None


async def _snapshot_surface(client: Client) -> PublicSurface:
    return PublicSurface.build(
        tools=await _collect_identifiers(client.list_tools, "tools", "name"),
        resources=await _collect_identifiers(client.list_resources, "resources", "uri"),
        resource_templates=await _collect_identifiers(
            client.list_resource_templates,
            "resource_templates",
            "uri_template",
        ),
        prompts=await _collect_identifiers(client.list_prompts, "prompts", "name"),
    )


async def _collect_identifiers(
    fetch: Callable[..., Awaitable[Any]],
    collection_name: str,
    identifier_name: str,
) -> list[str]:
    if _SURFACE_COLLECTION_FIELDS.get(collection_name) != identifier_name:
        raise _request_failure(RuntimeCode.PAGINATION_PAGE_INVALID)

    identifiers: list[str] = []
    seen_cursors: set[str] = set()
    cursor: str | None = None
    page_count = 0
    missing = object()
    while True:
        if page_count >= _MAX_SURFACE_PAGES:
            raise _request_failure(RuntimeCode.PAGINATION_PAGE_LIMIT)
        page = await fetch(cursor=cursor, cache_mode="refresh")
        page_count += 1
        page_items = getattr(page, collection_name, missing)
        next_cursor = getattr(page, "next_cursor", missing)
        if not isinstance(page_items, list) or (
            next_cursor is not None
            and (not isinstance(next_cursor, str) or not next_cursor or len(next_cursor) > _MAX_SURFACE_CURSOR_LENGTH)
        ):
            raise _request_failure(RuntimeCode.PAGINATION_PAGE_INVALID)

        for item in page_items:
            identifier = getattr(item, identifier_name, missing)
            if not isinstance(identifier, str) or not identifier or len(identifier) > _MAX_SURFACE_IDENTIFIER_LENGTH:
                raise _request_failure(RuntimeCode.PAGINATION_ITEM_INVALID)
            if len(identifiers) >= _MAX_SURFACE_IDENTIFIERS:
                raise _request_failure(RuntimeCode.PAGINATION_IDENTIFIER_LIMIT)
            identifiers.append(identifier)

        if next_cursor is None:
            return identifiers
        if next_cursor in seen_cursors:
            raise _request_failure(RuntimeCode.PAGINATION_CURSOR_REPEATED)
        seen_cursors.add(next_cursor)
        cursor = next_cursor


async def _render_seed(client: Client, fixture_path: Path) -> _ArtifactSeed:
    result = await client.call_tool(
        "render_preview_batch",
        {
            "request": {
                "input_paths": [str(fixture_path)],
                "pipeline": {"transforms": [{"name": "HorizontalFlip", "params": {}, "p": 1.0}]},
                "variants_per_image": 1,
                "seed": 17,
            }
        },
    )
    content = result.structured_content
    if result.is_error or not isinstance(content, Mapping):
        raise _request_failure(RuntimeCode.TOOL_RESULT_INVALID)

    run_id = content.get("run_id")
    if not isinstance(run_id, str) or _RUN_ID_PATTERN.fullmatch(run_id) is None:
        raise _request_failure(RuntimeCode.TOOL_RESULT_INVALID)
    artifact = _contact_sheet_artifact(content, run_id)
    payload = await _read_png_resource(client, artifact.uri)
    digest = _validate_artifact_payload(artifact, payload)
    return _ArtifactSeed(
        run_id=run_id,
        contact_sheet_uri=artifact.uri,
        contact_sheet_sha256=digest,
    )


async def _read_old_artifact(client: Client, seed: _ArtifactSeed) -> ArtifactContinuity:
    manifest = await client.call_tool("get_preview_manifest", {"run_id": seed.run_id})
    manifest_content = manifest.structured_content
    if manifest.is_error or not isinstance(manifest_content, Mapping):
        raise _request_failure(RuntimeCode.MANIFEST_INVALID)
    run_id = manifest_content.get("run_id")
    if not isinstance(run_id, str) or _RUN_ID_PATTERN.fullmatch(run_id) is None:
        raise _request_failure(RuntimeCode.MANIFEST_INVALID)
    if run_id != seed.run_id:
        raise _request_failure(RuntimeCode.MANIFEST_RUN_ID_MISMATCH)
    artifact = _contact_sheet_artifact(
        manifest_content,
        run_id,
        uri_failure=RuntimeCode.CONTACT_SHEET_URI_MISMATCH,
    )

    payload = await _read_png_resource(client, artifact.uri)
    digest = _validate_artifact_payload(
        artifact,
        payload,
        seed_digest=seed.contact_sheet_sha256,
    )

    return ArtifactContinuity(
        manifest_readable=True,
        manifest_run_id_matches=True,
        contact_sheet_readable=True,
        content_unchanged=True,
        contact_sheet_sha256=digest,
    )


def _contact_sheet_artifact(
    content: Mapping[str, Any],
    run_id: str,
    *,
    uri_failure: RuntimeCode = RuntimeCode.CONTACT_SHEET_ARTIFACT_INVALID,
) -> _ContactSheetArtifact:
    artifacts = content.get("artifacts")
    if not isinstance(artifacts, list):
        raise _request_failure(RuntimeCode.MANIFEST_INVALID)
    if any(not isinstance(artifact, Mapping) for artifact in artifacts):
        raise _request_failure(RuntimeCode.MANIFEST_INVALID)
    contact_sheets = [artifact for artifact in artifacts if artifact.get("kind") == "contact_sheet"]
    if len(contact_sheets) != 1:
        raise _request_failure(RuntimeCode.CONTACT_SHEET_COUNT_INVALID)

    contact_sheet = contact_sheets[0]
    uri = contact_sheet.get("uri")
    mime_type = contact_sheet.get("mime_type")
    size_bytes = contact_sheet.get("size_bytes")
    digest = contact_sheet.get("sha256")
    if not isinstance(uri, str) or uri != f"artifact://{run_id}/contact_sheet.png":
        raise _request_failure(uri_failure)
    if (
        mime_type != "image/png"
        or type(size_bytes) is not int
        or size_bytes < 0
        or size_bytes > _MAX_PNG_DECODED_BYTES
        or not isinstance(digest, str)
        or _LOWER_SHA256_PATTERN.fullmatch(digest) is None
    ):
        raise _request_failure(RuntimeCode.CONTACT_SHEET_ARTIFACT_INVALID)
    return _ContactSheetArtifact(
        uri=uri,
        mime_type=mime_type,
        size_bytes=size_bytes,
        sha256=digest,
    )


def _validate_artifact_payload(
    artifact: _ContactSheetArtifact,
    payload: bytes,
    *,
    seed_digest: str | None = None,
) -> str:
    if len(payload) != artifact.size_bytes:
        raise _request_failure(RuntimeCode.ARTIFACT_SIZE_MISMATCH)
    digest = hashlib.sha256(payload).hexdigest()
    if digest != artifact.sha256:
        raise _request_failure(RuntimeCode.ARTIFACT_DIGEST_MISMATCH)
    if seed_digest is not None and digest != seed_digest:
        raise _request_failure(RuntimeCode.ARTIFACT_SEED_DIGEST_MISMATCH)
    return digest


def _request_failure(code: RuntimeCode) -> PublishedUpgradeRuntimeError:
    return PublishedUpgradeRuntimeError(
        phase=RuntimePhase.REQUEST,
        code=code,
    )


async def _read_png_resource(client: Client, uri: str) -> bytes:
    result = await client.read_resource(uri)
    if len(result.contents) != 1:
        raise _request_failure(RuntimeCode.RESOURCE_CONTENT_COUNT_INVALID)
    content = result.contents[0]
    if not isinstance(content, BlobResourceContents):
        raise _request_failure(RuntimeCode.RESOURCE_CONTENT_TYPE_INVALID)
    if str(content.uri) != uri:
        raise _request_failure(RuntimeCode.RESOURCE_URI_MISMATCH)
    if content.mime_type != "image/png":
        raise _request_failure(RuntimeCode.RESOURCE_MIME_INVALID)
    if len(content.blob) > _MAX_PNG_ENCODED_BYTES:
        raise _request_failure(RuntimeCode.RESOURCE_ENCODED_TOO_LARGE)
    try:
        payload = base64.b64decode(content.blob, validate=True)
    except ValueError:
        raise _request_failure(RuntimeCode.RESOURCE_BASE64_INVALID) from None
    if len(payload) > _MAX_PNG_DECODED_BYTES:
        raise _request_failure(RuntimeCode.RESOURCE_DECODED_TOO_LARGE)
    if not payload.startswith(b"\x89PNG\r\n\x1a\n"):
        raise _request_failure(RuntimeCode.RESOURCE_PNG_INVALID)
    try:
        with Image.open(BytesIO(payload)) as decoded:
            _validate_png_image(decoded)
            decoded.verify()
        with Image.open(BytesIO(payload)) as decoded:
            _validate_png_image(decoded)
            decoded.load()
    except (Image.DecompressionBombError, OSError, SyntaxError, ValueError):
        raise _request_failure(RuntimeCode.RESOURCE_PNG_INVALID) from None
    return payload


def _validate_png_image(image: Image.Image) -> None:
    width, height = image.size
    if image.format != "PNG":
        raise _request_failure(RuntimeCode.RESOURCE_PNG_INVALID)
    if (
        width <= 0
        or height <= 0
        or width > _MAX_PNG_WIDTH
        or height > _MAX_PNG_HEIGHT
        or width * height > _MAX_PNG_PIXELS
    ):
        raise _request_failure(RuntimeCode.RESOURCE_DIMENSIONS_INVALID)
