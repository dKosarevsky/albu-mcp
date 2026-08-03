from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import struct
import sys
import zlib
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from dataclasses import replace
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from mcp import Client
from mcp.types import BlobResourceContents, CallToolResult, ReadResourceResult, TextResourceContents
from mcp.types.version import LATEST_HANDSHAKE_VERSION, LATEST_MODERN_VERSION
from PIL import Image
from typing_extensions import Self

from albumentationsx_mcp import server as server_module
from albumentationsx_mcp.server import ServerSettings
from scripts import published_upgrade_runtime as runtime_module
from scripts.published_upgrade_runtime import (
    PUBLISHED_SERVER_BOOTSTRAP,
    PublishedUpgradeConfig,
    PublishedUpgradeRuntimeError,
    RuntimeCode,
    RuntimePhase,
    ServerClientRequest,
    StderrCategory,
    build_attested_uvx_server_command,
    build_uvx_server_command,
    clean_subprocess_environment,
    open_published_client,
    run_published_upgrade,
)

if sys.version_info >= (3, 11):
    from builtins import ExceptionGroup as RuntimeExceptionGroup
else:
    from exceptiongroup import ExceptionGroup as RuntimeExceptionGroup  # ty: ignore[unresolved-import]


def _config(tmp_path: Path) -> PublishedUpgradeConfig:
    return PublishedUpgradeConfig(
        from_version="1.20.0",
        to_version="1.21.0",
        observed_on="2026-08-03",
        allowed_root=tmp_path,
        artifact_root=tmp_path / "artifacts",
        read_timeout_seconds=20.0,
    )


class _FailingSurfaceClient:
    def __init__(self, failure: BaseException, events: list[str] | None = None) -> None:
        self.failure = failure
        self.events = events

    async def list_tools(self, **_kwargs: object) -> object:
        if self.events is not None:
            self.events.append("request")
        raise self.failure


class _ResourceClient:
    def __init__(self, result: ReadResourceResult) -> None:
        self.result = result
        self.read_uris: list[str] = []

    async def read_resource(self, uri: str) -> ReadResourceResult:
        self.read_uris.append(uri)
        return self.result


class _ArtifactClient(_ResourceClient):
    def __init__(self, tool_result: CallToolResult, resource_result: ReadResourceResult) -> None:
        super().__init__(resource_result)
        self.tool_result = tool_result
        self.tool_calls: list[tuple[str, dict[str, object]]] = []

    async def call_tool(self, name: str, arguments: dict[str, object]) -> CallToolResult:
        self.tool_calls.append((name, arguments))
        return self.tool_result


_RUN_ID = "a" * 32
_OTHER_RUN_ID = "b" * 32
_CONTACT_SHEET_URI = f"artifact://{_RUN_ID}/contact_sheet.png"
_OTHER_CONTACT_SHEET_URI = f"artifact://{_OTHER_RUN_ID}/contact_sheet.png"


def _png_bytes(size: tuple[int, int] = (24, 24)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, (96, 128, 160)).save(buffer, format="PNG")
    return buffer.getvalue()


def _blob_result(
    payload: bytes,
    *,
    uri: str = _CONTACT_SHEET_URI,
    mime_type: str = "image/png",
) -> ReadResourceResult:
    return ReadResourceResult(
        contents=[
            BlobResourceContents(
                uri=uri,
                mime_type=mime_type,
                blob=base64.b64encode(payload).decode("ascii"),
            )
        ]
    )


def _artifact(payload: bytes, **overrides: object) -> dict[str, object]:
    artifact: dict[str, object] = {
        "kind": "contact_sheet",
        "uri": _CONTACT_SHEET_URI,
        "mime_type": "image/png",
        "size_bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }
    artifact.update(overrides)
    return artifact


def _manifest_result(
    payload: bytes,
    *,
    run_id: str = _RUN_ID,
    artifacts: Sequence[object] | None = None,
    is_error: bool = False,
) -> CallToolResult:
    return CallToolResult(
        content=[],
        structured_content={
            "run_id": run_id,
            "artifacts": [_artifact(payload)] if artifacts is None else list(artifacts),
        },
        is_error=is_error,
    )


def _corrupt_idat_with_valid_crc(payload: bytes) -> bytes:
    output = bytearray(payload[:8])
    offset = 8
    replaced = False
    while offset < len(payload):
        length = struct.unpack(">I", payload[offset : offset + 4])[0]
        chunk_type = payload[offset + 4 : offset + 8]
        chunk_data = payload[offset + 8 : offset + 8 + length]
        if chunk_type == b"IDAT" and not replaced:
            chunk_data = b"\x00" * length
            replaced = True
        output.extend(struct.pack(">I", len(chunk_data)))
        output.extend(chunk_type)
        output.extend(chunk_data)
        output.extend(struct.pack(">I", zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF))
        offset += 12 + length
    assert replaced
    return bytes(output)


def test_build_uvx_server_command_pins_exact_package_version() -> None:
    assert build_uvx_server_command("1.20.0") == [
        "uvx",
        "--from",
        "albumentationsx-mcp==1.20.0",
        "--refresh-package",
        "albumentationsx-mcp",
        "albumentationsx-mcp",
    ]


def test_attested_uvx_command_uses_isolated_same_process_bootstrap() -> None:
    assert build_attested_uvx_server_command("1.20.0") == [
        "uvx",
        "--from",
        "albumentationsx-mcp==1.20.0",
        "--refresh-package",
        "albumentationsx-mcp",
        "--isolated",
        "--no-config",
        "--no-env-file",
        "--no-sources",
        "python",
        "-I",
        "-c",
        PUBLISHED_SERVER_BOOTSTRAP,
        "1.20.0",
    ]
    assert "\n" in PUBLISHED_SERVER_BOOTSTRAP
    assert 'version("albumentationsx-mcp")' in PUBLISHED_SERVER_BOOTSTRAP
    assert "if observed_version != expected_version:" in PUBLISHED_SERVER_BOOTSTRAP
    assert "raise SystemExit(86)" in PUBLISHED_SERVER_BOOTSTRAP
    assert "albumentationsx_mcp.cli.main()" in PUBLISHED_SERVER_BOOTSTRAP


def test_clean_environment_removes_albumentationsx_runtime_overrides() -> None:
    cleaned = clean_subprocess_environment(
        {
            "PATH": "/bin",
            "HTTPS_PROXY": "http://proxy.invalid",
            "ALBU_MCP_ALLOWED_ROOTS": "/private/input",
            "ALBU_MCP_CAPABILITY_PROFILE": "core",
        }
    )

    assert cleaned == {"PATH": "/bin", "HTTPS_PROXY": "http://proxy.invalid"}


def test_clean_environment_allows_only_runtime_network_and_certificate_essentials() -> None:
    environment = {
        "PATH": "/bin",
        "HOME": "/home/probe",
        "LOGNAME": "probe",
        "SHELL": "/bin/sh",
        "TERM": "dumb",
        "USER": "probe",
        "TMPDIR": "/runtime/temp",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "HTTPS_PROXY": "http://proxy.invalid",
        "http_proxy": "http://proxy.invalid",
        "ALL_PROXY": "socks5://proxy.invalid",
        "NO_PROXY": "localhost",
        "SSL_CERT_FILE": "/certs/ca.pem",
        "SSL_CERT_DIR": "/certs",
        "REQUESTS_CA_BUNDLE": "/certs/requests.pem",
        "CURL_CA_BUNDLE": "/certs/curl.pem",
        "ALBU_MCP_ALLOWED_ROOTS": "/private/input",
        "PYTHONPATH": "/private/source",
        "PYTHONHOME": "/private/python",
        "UV_INDEX": "https://token@private.invalid/simple",
        "UV_PROJECT": "/private/project",
        "UV_SOURCES": "local",
        "UV_CONFIG_FILE": "/private/uv.toml",
        "GITHUB_TOKEN": "secret",
        "AWS_SECRET_ACCESS_KEY": "secret",
        "OPENAI_API_KEY": "secret",
        "DATABASE_URL": "postgres://secret",
        "ARBITRARY_SECRET": "secret",
    }

    cleaned = clean_subprocess_environment(environment)

    assert cleaned == {
        "PATH": "/bin",
        "HOME": "/home/probe",
        "LOGNAME": "probe",
        "SHELL": "/bin/sh",
        "TERM": "dumb",
        "USER": "probe",
        "TMPDIR": "/runtime/temp",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "HTTPS_PROXY": "http://proxy.invalid",
        "http_proxy": "http://proxy.invalid",
        "ALL_PROXY": "socks5://proxy.invalid",
        "NO_PROXY": "localhost",
        "SSL_CERT_FILE": "/certs/ca.pem",
        "SSL_CERT_DIR": "/certs",
        "REQUESTS_CA_BUNDLE": "/certs/requests.pem",
        "CURL_CA_BUNDLE": "/certs/curl.pem",
    }


def test_runtime_error_has_finite_privacy_safe_serialization() -> None:
    error = PublishedUpgradeRuntimeError(
        phase=RuntimePhase.REQUEST,
        code=RuntimeCode.REQUEST_FAILED,
        diagnostic=StderrCategory.OTHER,
    )

    encoded = json.dumps(error.to_dict(), sort_keys=True)

    assert str(error) == "Published upgrade probe failed."
    assert error.args == ("Published upgrade probe failed.",)
    assert error.phase is RuntimePhase.REQUEST
    assert error.code is RuntimeCode.REQUEST_FAILED
    assert error.diagnostic is StderrCategory.OTHER
    assert json.loads(encoded) == {
        "code": "request_failed",
        "diagnostic": "other",
        "message": "Published upgrade probe failed.",
        "phase": "request",
    }
    assert len(encoded) < 200


def test_client_factory_connect_failure_is_normalized_and_fixture_is_cleaned(tmp_path: Path) -> None:
    secret = str(tmp_path / "private-connect-token")

    @asynccontextmanager
    async def client_factory(_request: ServerClientRequest) -> AsyncIterator[Client]:
        raise OSError(secret)
        yield cast("Client", object())

    with pytest.raises(PublishedUpgradeRuntimeError) as caught:
        asyncio.run(run_published_upgrade(_config(tmp_path), client_factory=client_factory))

    assert caught.value.phase is RuntimePhase.STARTUP
    assert caught.value.code is RuntimeCode.CLIENT_CONNECT_FAILED
    assert secret not in str(caught.value)
    assert secret not in json.dumps(caught.value.to_dict())
    assert list(tmp_path.glob(".published-upgrade-*")) == []


def test_fixture_workspace_rejects_symlink_allowed_root_before_client_start(tmp_path: Path) -> None:
    physical_root = tmp_path / "physical"
    physical_root.mkdir()
    allowed_root = tmp_path / "private-allowed-root"
    allowed_root.symlink_to(physical_root, target_is_directory=True)
    starts = 0

    @asynccontextmanager
    async def client_factory(_request: ServerClientRequest) -> AsyncIterator[Client]:
        nonlocal starts
        starts += 1
        yield cast("Client", object())

    config = replace(_config(tmp_path), allowed_root=allowed_root)
    with pytest.raises(PublishedUpgradeRuntimeError) as caught:
        asyncio.run(run_published_upgrade(config, client_factory=client_factory))

    assert starts == 0
    assert caught.value.phase is RuntimePhase.FILESYSTEM
    assert caught.value.code is RuntimeCode.ALLOWED_ROOT_INVALID
    assert str(allowed_root) not in json.dumps(caught.value.to_dict())


def test_fixture_workspace_creation_failure_is_normalized(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = str(tmp_path / "private-create-token")

    def fail_creation(*_args: object, **_kwargs: object) -> str:
        raise OSError(secret)

    monkeypatch.setattr(runtime_module.tempfile, "mkdtemp", fail_creation)
    with pytest.raises(PublishedUpgradeRuntimeError) as caught:
        asyncio.run(run_published_upgrade(_config(tmp_path)))

    assert caught.value.phase is RuntimePhase.FILESYSTEM
    assert caught.value.code is RuntimeCode.FIXTURE_CREATE_FAILED
    assert secret not in repr(caught.value)


def test_fixture_cleanup_failure_is_normalized(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture_root, _fixture_path = runtime_module._create_fixture_workspace(tmp_path)
    secret = str(tmp_path / "private-cleanup-token")

    def fail_cleanup(_path: Path) -> None:
        raise OSError(secret)

    monkeypatch.setattr(runtime_module.shutil, "rmtree", fail_cleanup)
    with pytest.raises(PublishedUpgradeRuntimeError) as caught:
        runtime_module._remove_fixture_workspace(fixture_root)

    assert caught.value.phase is RuntimePhase.FILESYSTEM
    assert caught.value.code is RuntimeCode.FIXTURE_CLEANUP_FAILED
    assert secret not in json.dumps(caught.value.to_dict())


def test_fixture_cleanup_rejects_symlink_without_following_it(tmp_path: Path) -> None:
    target = tmp_path / "private-target"
    target.mkdir()
    marker = target / "marker"
    marker.write_text("retained", encoding="utf-8")
    fixture_link = tmp_path / ".published-upgrade-link"
    fixture_link.symlink_to(target, target_is_directory=True)

    with pytest.raises(PublishedUpgradeRuntimeError) as caught:
        runtime_module._remove_fixture_workspace(fixture_link)

    assert caught.value.phase is RuntimePhase.FILESYSTEM
    assert caught.value.code is RuntimeCode.FIXTURE_CLEANUP_FAILED
    assert marker.read_text(encoding="utf-8") == "retained"


def test_stdio_child_start_failure_is_normalized_without_raw_exception(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = str(tmp_path / "private-child-token")

    @asynccontextmanager
    async def failing_stdio_client(*_args: object, **_kwargs: object) -> AsyncIterator[object]:
        raise OSError(secret)
        yield object()

    monkeypatch.setattr(runtime_module, "stdio_client", failing_stdio_client)
    request = ServerClientRequest(
        version="1.20.0",
        mode="legacy",
        allowed_root=tmp_path,
        artifact_root=tmp_path / "artifacts",
        read_timeout_seconds=20.0,
    )

    async def connect() -> None:
        async with open_published_client(request):
            message = "unreachable"
            raise AssertionError(message)

    with pytest.raises(PublishedUpgradeRuntimeError) as caught:
        asyncio.run(connect())

    assert caught.value.phase is RuntimePhase.STARTUP
    assert caught.value.code is RuntimeCode.CHILD_START_FAILED
    assert secret not in repr(caught.value)


def test_negotiation_failure_is_distinct_from_child_start_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    @asynccontextmanager
    async def connected_stdio_client(*_args: object, **_kwargs: object) -> AsyncIterator[object]:
        yield object()

    class NegotiationFailingClient:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        async def __aenter__(self) -> Self:
            message = "private-negotiation-group"
            raise RuntimeExceptionGroup(message, [ValueError("private-negotiation-value")])

        async def __aexit__(self, *_args: object) -> None:
            return None

    monkeypatch.setattr(runtime_module, "stdio_client", connected_stdio_client)
    monkeypatch.setattr(runtime_module, "Client", NegotiationFailingClient)
    request = ServerClientRequest(
        version="1.20.0",
        mode="legacy",
        allowed_root=tmp_path,
        artifact_root=tmp_path / "artifacts",
        read_timeout_seconds=20.0,
    )

    async def connect() -> None:
        async with open_published_client(request):
            message = "unreachable"
            raise AssertionError(message)

    with pytest.raises(PublishedUpgradeRuntimeError) as caught:
        asyncio.run(connect())

    assert caught.value.phase is RuntimePhase.NEGOTIATION
    assert caught.value.code is RuntimeCode.NEGOTIATION_FAILED
    assert "private" not in json.dumps(caught.value.to_dict())


def test_bounded_stderr_sink_classifies_without_retaining_raw_output() -> None:
    sink = runtime_module._BoundedStderrSink()
    with sink:
        os.write(sink.stream.fileno(), b"private server failure\n")

    assert sink.category is StderrCategory.OTHER
    assert all(value not in {"private server failure", b"private server failure"} for value in vars(sink).values())


@pytest.mark.parametrize(
    ("failure", "expected_code"),
    [
        (ValueError("private-request-value"), RuntimeCode.REQUEST_FAILED),
        (
            RuntimeExceptionGroup(
                "private-group-value",
                [ValueError("private-child-value"), TimeoutError("private-timeout-value")],
            ),
            RuntimeCode.TIMEOUT,
        ),
    ],
)
def test_request_failures_and_nested_timeouts_are_normalized(
    tmp_path: Path,
    failure: BaseException,
    expected_code: RuntimeCode,
) -> None:
    @asynccontextmanager
    async def client_factory(_request: ServerClientRequest) -> AsyncIterator[Client]:
        yield cast("Client", _FailingSurfaceClient(failure))

    with pytest.raises(PublishedUpgradeRuntimeError) as caught:
        asyncio.run(run_published_upgrade(_config(tmp_path), client_factory=client_factory))

    assert caught.value.phase is RuntimePhase.REQUEST
    assert caught.value.code is expected_code
    encoded = json.dumps(caught.value.to_dict())
    assert "private" not in encoded


def test_existing_runtime_error_survives_exit_and_cleanup_failures_in_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    existing = PublishedUpgradeRuntimeError(
        phase=RuntimePhase.REQUEST,
        code=RuntimeCode.REQUEST_FAILED,
    )
    remove_fixture_workspace = runtime_module._remove_fixture_workspace

    def fail_after_cleanup(fixture_root: Path) -> None:
        events.append("cleanup")
        remove_fixture_workspace(fixture_root)
        message = "private-cleanup-value"
        raise OSError(message)

    monkeypatch.setattr(runtime_module, "_remove_fixture_workspace", fail_after_cleanup)

    @asynccontextmanager
    async def client_factory(_request: ServerClientRequest) -> AsyncIterator[Client]:
        events.append("enter")
        try:
            yield cast("Client", _FailingSurfaceClient(existing, events))
        finally:
            events.append("exit")
            message = "private-exit-value"
            raise OSError(message)

    with pytest.raises(PublishedUpgradeRuntimeError) as caught:
        asyncio.run(run_published_upgrade(_config(tmp_path), client_factory=client_factory))
    events.append("caught")

    assert caught.value is existing
    assert events == ["enter", "request", "exit", "cleanup", "caught"]


def test_context_exit_failure_after_success_is_normalized(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    @asynccontextmanager
    async def client_factory(request: ServerClientRequest) -> AsyncIterator[Client]:
        monkeypatch.setattr(server_module, "_package_version", lambda: "2.0.0")
        server = server_module.create_mcp_server(
            ServerSettings(
                allowed_roots=[request.allowed_root],
                artifact_root=request.artifact_root,
            )
        )
        async with Client(server, mode=request.mode) as client:
            yield client
        message = "private-exit-group"
        raise RuntimeExceptionGroup(message, [ValueError("private-exit-value")])

    with pytest.raises(PublishedUpgradeRuntimeError) as caught:
        asyncio.run(run_published_upgrade(_config(tmp_path), client_factory=client_factory))

    assert caught.value.phase is RuntimePhase.CONTEXT_EXIT
    assert caught.value.code is RuntimeCode.CONTEXT_EXIT_FAILED
    assert "private" not in json.dumps(caught.value.to_dict())


def test_cancellation_is_not_normalized(tmp_path: Path) -> None:
    @asynccontextmanager
    async def client_factory(_request: ServerClientRequest) -> AsyncIterator[Client]:
        raise asyncio.CancelledError
        yield cast("Client", object())

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(run_published_upgrade(_config(tmp_path), client_factory=client_factory))


def _assert_png_failure(result: ReadResourceResult, code: RuntimeCode) -> None:
    client = _ResourceClient(result)
    with pytest.raises(PublishedUpgradeRuntimeError) as caught:
        asyncio.run(runtime_module._read_png_resource(cast("Client", client), _CONTACT_SHEET_URI))
    assert caught.value.phase is RuntimePhase.REQUEST
    assert caught.value.code is code


@pytest.mark.parametrize("content_count", [0, 2])
def test_png_resource_requires_exactly_one_content(content_count: int) -> None:
    blob = _blob_result(_png_bytes()).contents[0]
    _assert_png_failure(
        ReadResourceResult(contents=[blob] * content_count),
        RuntimeCode.RESOURCE_CONTENT_COUNT_INVALID,
    )


def test_png_resource_rejects_wrong_content_type_and_mime() -> None:
    text = TextResourceContents(uri=_CONTACT_SHEET_URI, mime_type="text/plain", text="private")
    _assert_png_failure(
        ReadResourceResult(contents=[text]),
        RuntimeCode.RESOURCE_CONTENT_TYPE_INVALID,
    )
    _assert_png_failure(
        _blob_result(_png_bytes(), mime_type="image/jpeg"),
        RuntimeCode.RESOURCE_MIME_INVALID,
    )


def test_png_resource_rejects_invalid_base64_and_signature() -> None:
    _assert_png_failure(
        ReadResourceResult(
            contents=[
                BlobResourceContents(
                    uri=_CONTACT_SHEET_URI,
                    mime_type="image/png",
                    blob="%%%not-base64%%%",
                )
            ]
        ),
        RuntimeCode.RESOURCE_BASE64_INVALID,
    )
    _assert_png_failure(
        _blob_result(b"not a png"),
        RuntimeCode.RESOURCE_PNG_INVALID,
    )


def test_png_resource_caps_encoded_and_decoded_size(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _png_bytes()
    encoded = base64.b64encode(payload).decode("ascii")
    result = ReadResourceResult(
        contents=[
            BlobResourceContents(
                uri=_CONTACT_SHEET_URI,
                mime_type="image/png",
                blob=encoded,
            )
        ]
    )

    monkeypatch.setattr(runtime_module, "_MAX_PNG_ENCODED_BYTES", len(encoded) - 1)
    _assert_png_failure(result, RuntimeCode.RESOURCE_ENCODED_TOO_LARGE)
    monkeypatch.setattr(runtime_module, "_MAX_PNG_ENCODED_BYTES", len(encoded))
    monkeypatch.setattr(runtime_module, "_MAX_PNG_DECODED_BYTES", len(payload) - 1)
    _assert_png_failure(result, RuntimeCode.RESOURCE_DECODED_TOO_LARGE)


def test_png_resource_reopens_and_loads_corrupt_idat() -> None:
    corrupt = _corrupt_idat_with_valid_crc(_png_bytes())

    with Image.open(BytesIO(corrupt)) as image:
        image.verify()

    _assert_png_failure(
        _blob_result(corrupt),
        RuntimeCode.RESOURCE_PNG_INVALID,
    )


def test_png_resource_caps_dimensions_and_accepts_valid_png(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _png_bytes((33, 2))
    result = _blob_result(payload)

    monkeypatch.setattr(runtime_module, "_MAX_PNG_WIDTH", 32)
    _assert_png_failure(result, RuntimeCode.RESOURCE_DIMENSIONS_INVALID)
    monkeypatch.setattr(runtime_module, "_MAX_PNG_WIDTH", 33)

    client = _ResourceClient(result)
    assert asyncio.run(runtime_module._read_png_resource(cast("Client", client), _CONTACT_SHEET_URI)) == payload
    assert client.read_uris == [_CONTACT_SHEET_URI]


def _render_seed(payload: bytes, *, artifacts: list[object] | None = None) -> runtime_module._ArtifactSeed:
    client = _ArtifactClient(
        _manifest_result(payload, artifacts=artifacts),
        _blob_result(payload),
    )
    return asyncio.run(runtime_module._render_seed(cast("Client", client), Path("fixture.png")))


@pytest.mark.parametrize(
    "artifacts",
    [
        [],
        [_artifact(_png_bytes()), _artifact(_png_bytes())],
    ],
)
def test_seed_manifest_requires_exactly_one_contact_sheet(artifacts: list[object]) -> None:
    payload = _png_bytes()
    client = _ArtifactClient(
        _manifest_result(payload, artifacts=artifacts),
        _blob_result(payload),
    )

    with pytest.raises(PublishedUpgradeRuntimeError) as caught:
        asyncio.run(runtime_module._render_seed(cast("Client", client), Path("fixture.png")))

    assert caught.value.code is RuntimeCode.CONTACT_SHEET_COUNT_INVALID


@pytest.mark.parametrize(
    ("overrides", "expected_code"),
    [
        ({"uri": "artifact://bad/../private.png"}, RuntimeCode.CONTACT_SHEET_ARTIFACT_INVALID),
        ({"mime_type": "image/jpeg"}, RuntimeCode.CONTACT_SHEET_ARTIFACT_INVALID),
        ({"size_bytes": -1}, RuntimeCode.CONTACT_SHEET_ARTIFACT_INVALID),
        ({"size_bytes": True}, RuntimeCode.CONTACT_SHEET_ARTIFACT_INVALID),
        ({"sha256": "A" * 64}, RuntimeCode.CONTACT_SHEET_ARTIFACT_INVALID),
    ],
)
def test_seed_manifest_rejects_malformed_contact_sheet_descriptor(
    overrides: dict[str, object],
    expected_code: RuntimeCode,
) -> None:
    payload = _png_bytes()
    client = _ArtifactClient(
        _manifest_result(payload, artifacts=[_artifact(payload, **overrides)]),
        _blob_result(payload),
    )

    with pytest.raises(PublishedUpgradeRuntimeError) as caught:
        asyncio.run(runtime_module._render_seed(cast("Client", client), Path("fixture.png")))

    assert caught.value.code is expected_code


def test_seed_rejects_failed_or_malformed_tool_result() -> None:
    payload = _png_bytes()
    cases = [
        CallToolResult(content=[], structured_content=None, is_error=True),
        CallToolResult(content=[], structured_content={"run_id": "bad", "artifacts": [_artifact(payload)]}),
    ]
    for result in cases:
        client = _ArtifactClient(result, _blob_result(payload))
        with pytest.raises(PublishedUpgradeRuntimeError) as caught:
            asyncio.run(runtime_module._render_seed(cast("Client", client), Path("fixture.png")))
        assert caught.value.code is RuntimeCode.TOOL_RESULT_INVALID


def test_seed_manifest_matches_resource_size_and_digest() -> None:
    payload = _png_bytes()
    for overrides, expected_code in [
        ({"size_bytes": len(payload) + 1}, RuntimeCode.ARTIFACT_SIZE_MISMATCH),
        ({"sha256": "b" * 64}, RuntimeCode.ARTIFACT_DIGEST_MISMATCH),
    ]:
        client = _ArtifactClient(
            _manifest_result(payload, artifacts=[_artifact(payload, **overrides)]),
            _blob_result(payload),
        )
        with pytest.raises(PublishedUpgradeRuntimeError) as caught:
            asyncio.run(runtime_module._render_seed(cast("Client", client), Path("fixture.png")))
        assert caught.value.code is expected_code


def test_restored_manifest_requires_same_run_and_contact_sheet_uri() -> None:
    payload = _png_bytes()
    seed = _render_seed(payload)

    wrong_run_client = _ArtifactClient(
        _manifest_result(payload, run_id=_OTHER_RUN_ID),
        _blob_result(payload),
    )
    with pytest.raises(PublishedUpgradeRuntimeError) as wrong_run:
        asyncio.run(runtime_module._read_old_artifact(cast("Client", wrong_run_client), seed))
    assert wrong_run.value.code is RuntimeCode.MANIFEST_RUN_ID_MISMATCH

    different_uri_client = _ArtifactClient(
        _manifest_result(
            payload,
            artifacts=[_artifact(payload, uri=_OTHER_CONTACT_SHEET_URI)],
        ),
        _blob_result(payload, uri=_OTHER_CONTACT_SHEET_URI),
    )
    with pytest.raises(PublishedUpgradeRuntimeError) as different_uri:
        asyncio.run(runtime_module._read_old_artifact(cast("Client", different_uri_client), seed))
    assert different_uri.value.code is RuntimeCode.CONTACT_SHEET_URI_MISMATCH
    assert different_uri_client.read_uris == []


def test_restored_manifest_rejects_failed_or_malformed_result() -> None:
    payload = _png_bytes()
    seed = _render_seed(payload)
    cases = [
        CallToolResult(content=[], structured_content=None, is_error=True),
        CallToolResult(content=[], structured_content=["private"], is_error=False),
    ]
    for result in cases:
        client = _ArtifactClient(result, _blob_result(payload))
        with pytest.raises(PublishedUpgradeRuntimeError) as caught:
            asyncio.run(runtime_module._read_old_artifact(cast("Client", client), seed))
        assert caught.value.code is RuntimeCode.MANIFEST_INVALID


def test_restored_manifest_rejects_duplicate_and_malformed_contact_sheets() -> None:
    payload = _png_bytes()
    seed = _render_seed(payload)
    cases = [
        (
            [_artifact(payload), _artifact(payload)],
            RuntimeCode.CONTACT_SHEET_COUNT_INVALID,
        ),
        (
            [_artifact(payload, size_bytes=-1)],
            RuntimeCode.CONTACT_SHEET_ARTIFACT_INVALID,
        ),
    ]
    for artifacts, expected_code in cases:
        client = _ArtifactClient(
            _manifest_result(payload, artifacts=artifacts),
            _blob_result(payload),
        )
        with pytest.raises(PublishedUpgradeRuntimeError) as caught:
            asyncio.run(runtime_module._read_old_artifact(cast("Client", client), seed))
        assert caught.value.code is expected_code


def test_restored_resource_matches_manifest_and_seed_digest() -> None:
    payload = _png_bytes()
    seed = _render_seed(payload)

    valid_client = _ArtifactClient(_manifest_result(payload), _blob_result(payload))
    continuity = asyncio.run(runtime_module._read_old_artifact(cast("Client", valid_client), seed))
    assert continuity.content_unchanged is True
    assert valid_client.read_uris == [_CONTACT_SHEET_URI]

    for overrides, resource, expected_code in [
        (
            {"size_bytes": len(payload) + 1},
            _blob_result(payload),
            RuntimeCode.ARTIFACT_SIZE_MISMATCH,
        ),
        (
            {"sha256": "b" * 64},
            _blob_result(payload),
            RuntimeCode.ARTIFACT_DIGEST_MISMATCH,
        ),
    ]:
        client = _ArtifactClient(
            _manifest_result(payload, artifacts=[_artifact(payload, **overrides)]),
            resource,
        )
        with pytest.raises(PublishedUpgradeRuntimeError) as caught:
            asyncio.run(runtime_module._read_old_artifact(cast("Client", client), seed))
        assert caught.value.code is expected_code

    changed_seed = replace(seed, contact_sheet_sha256="b" * 64)
    changed_seed_client = _ArtifactClient(_manifest_result(payload), _blob_result(payload))
    with pytest.raises(PublishedUpgradeRuntimeError) as changed:
        asyncio.run(runtime_module._read_old_artifact(cast("Client", changed_seed_client), changed_seed))
    assert changed.value.code is RuntimeCode.ARTIFACT_SEED_DIGEST_MISMATCH


def test_pagination_collects_two_pages_through_refresh_api() -> None:
    calls: list[tuple[str | None, str]] = []
    pages = {
        None: SimpleNamespace(
            tools=[SimpleNamespace(name="first")],
            next_cursor="page-2",
        ),
        "page-2": SimpleNamespace(
            tools=[SimpleNamespace(name="second")],
            next_cursor=None,
        ),
    }

    async def fetch(*, cursor: str | None, cache_mode: str) -> object:
        calls.append((cursor, cache_mode))
        return pages[cursor]

    identifiers = asyncio.run(runtime_module._collect_identifiers(fetch, "tools", "name"))

    assert identifiers == ["first", "second"]
    assert calls == [(None, "refresh"), ("page-2", "refresh")]


def test_pagination_rejects_repeated_cursor() -> None:
    pages = {
        None: SimpleNamespace(tools=[SimpleNamespace(name="first")], next_cursor="repeat"),
        "repeat": SimpleNamespace(tools=[SimpleNamespace(name="second")], next_cursor="repeat"),
    }

    async def fetch(*, cursor: str | None, cache_mode: str) -> object:
        assert cache_mode == "refresh"
        return pages[cursor]

    with pytest.raises(PublishedUpgradeRuntimeError) as caught:
        asyncio.run(runtime_module._collect_identifiers(fetch, "tools", "name"))

    assert caught.value.code is RuntimeCode.PAGINATION_CURSOR_REPEATED


def test_pagination_caps_pages_and_total_identifiers(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    async def continuing_fetch(*, cursor: str | None, cache_mode: str) -> object:
        nonlocal calls
        calls += 1
        assert cache_mode == "refresh"
        return SimpleNamespace(
            tools=[SimpleNamespace(name="first")],
            next_cursor="next" if cursor is None else "later",
        )

    monkeypatch.setattr(runtime_module, "_MAX_SURFACE_PAGES", 1)
    with pytest.raises(PublishedUpgradeRuntimeError) as page_limit:
        asyncio.run(runtime_module._collect_identifiers(continuing_fetch, "tools", "name"))
    assert page_limit.value.code is RuntimeCode.PAGINATION_PAGE_LIMIT
    assert calls == 1

    async def crowded_fetch(*, cursor: str | None, cache_mode: str) -> object:
        assert cursor is None
        assert cache_mode == "refresh"
        return SimpleNamespace(
            tools=[SimpleNamespace(name="first"), SimpleNamespace(name="second")],
            next_cursor=None,
        )

    monkeypatch.setattr(runtime_module, "_MAX_SURFACE_IDENTIFIERS", 1)
    with pytest.raises(PublishedUpgradeRuntimeError) as identifier_limit:
        asyncio.run(runtime_module._collect_identifiers(crowded_fetch, "tools", "name"))
    assert identifier_limit.value.code is RuntimeCode.PAGINATION_IDENTIFIER_LIMIT


@pytest.mark.parametrize(
    "page",
    [
        object(),
        SimpleNamespace(tools="not-a-list", next_cursor=None),
        SimpleNamespace(tools=[], next_cursor=object()),
    ],
)
def test_pagination_rejects_malformed_page(page: object) -> None:
    async def fetch(*, cursor: str | None, cache_mode: str) -> object:
        assert cursor is None
        assert cache_mode == "refresh"
        return page

    with pytest.raises(PublishedUpgradeRuntimeError) as caught:
        asyncio.run(runtime_module._collect_identifiers(fetch, "tools", "name"))

    assert caught.value.code is RuntimeCode.PAGINATION_PAGE_INVALID


@pytest.mark.parametrize(
    "item",
    [
        object(),
        SimpleNamespace(),
        SimpleNamespace(name=object()),
        SimpleNamespace(name=""),
        SimpleNamespace(name="x" * 4097),
    ],
)
def test_pagination_rejects_malformed_identifier(item: object) -> None:
    async def fetch(*, cursor: str | None, cache_mode: str) -> object:
        assert cursor is None
        assert cache_mode == "refresh"
        return SimpleNamespace(tools=[item], next_cursor=None)

    with pytest.raises(PublishedUpgradeRuntimeError) as caught:
        asyncio.run(runtime_module._collect_identifiers(fetch, "tools", "name"))

    assert caught.value.code is RuntimeCode.PAGINATION_ITEM_INVALID


def test_upgrade_runtime_restarts_three_clients_and_reads_old_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[ServerClientRequest] = []
    events: list[tuple[str, str, str]] = []
    servers: list[object] = []
    fixture_paths: set[Path] = set()
    active_clients = 0
    max_active_clients = 0

    @asynccontextmanager
    async def client_factory(request: ServerClientRequest) -> AsyncIterator[Client]:
        nonlocal active_clients, max_active_clients
        assert active_clients == 0
        active_clients += 1
        max_active_clients = max(max_active_clients, active_clients)
        requests.append(request)
        events.append(("enter", request.version, request.mode))
        generated = list(request.allowed_root.glob("*.png"))
        assert len(generated) == 1
        fixture_paths.add(generated[0])
        monkeypatch.setattr(server_module, "_package_version", lambda: "2.0.0")
        server = server_module.create_mcp_server(
            ServerSettings(
                allowed_roots=[request.allowed_root],
                artifact_root=request.artifact_root,
            )
        )
        servers.append(server)
        try:
            async with Client(server, mode=request.mode) as client:
                yield client
        finally:
            active_clients -= 1
            events.append(("exit", request.version, request.mode))

    report = asyncio.run(
        run_published_upgrade(
            _config(tmp_path),
            client_factory=client_factory,
        )
    )
    encoded = json.dumps(report, sort_keys=True)

    assert report["status"] == "pass"
    assert [(item.version, item.mode) for item in requests] == [
        ("1.20.0", "legacy"),
        ("1.21.0", "legacy"),
        ("1.21.0", "auto"),
    ]
    assert report["matrix"][0]["negotiated_protocol"] == LATEST_HANDSHAKE_VERSION
    assert report["matrix"][0]["observed_server_version"] == "1.20.0"
    assert report["matrix"][0]["advertised_server_version"] == "2.0.0"
    assert report["matrix"][0]["server_version_ok"] is True
    assert report["matrix"][2]["client_mode"] == LATEST_MODERN_VERSION
    assert report["matrix"][2]["negotiated_protocol"] == LATEST_MODERN_VERSION
    assert report["artifact_continuity"]["content_unchanged"] is True
    assert str(tmp_path) not in encoded
    assert max_active_clients == 1
    assert active_clients == 0
    assert len(servers) == 3
    assert len({id(server) for server in servers}) == 3
    assert events == [
        ("enter", "1.20.0", "legacy"),
        ("exit", "1.20.0", "legacy"),
        ("enter", "1.21.0", "legacy"),
        ("exit", "1.21.0", "legacy"),
        ("enter", "1.21.0", "auto"),
        ("exit", "1.21.0", "auto"),
    ]
    assert len({request.allowed_root for request in requests}) == 1
    fixture_root = requests[0].allowed_root
    assert fixture_root.parent == tmp_path
    assert not fixture_root.exists()
    assert all(not path.exists() for path in fixture_paths)
    assert any((tmp_path / "artifacts").rglob("contact_sheet.png"))
