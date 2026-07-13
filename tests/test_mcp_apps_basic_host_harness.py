from pathlib import Path

import pytest
from starlette.middleware.cors import CORSMiddleware

from scripts.run_mcp_apps_basic_host_harness import (
    build_basic_host_app,
    validate_loopback_origin,
)


@pytest.mark.parametrize(
    "origin",
    [
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "https://[::1]:8443",
    ],
)
def test_validate_loopback_origin_accepts_local_hosts(origin: str) -> None:
    assert validate_loopback_origin(origin) == origin


@pytest.mark.parametrize(
    "origin",
    [
        "https://example.com",
        "http://*.localhost:8080",
        "http://localhost:8080/path",
        "http://user@localhost:8080",
        "file:///tmp/host.html",
    ],
)
def test_validate_loopback_origin_rejects_non_origin_values(origin: str) -> None:
    with pytest.raises(ValueError, match="loopback HTTP origin"):
        validate_loopback_origin(origin)


def test_build_basic_host_app_scopes_cors_to_one_origin(tmp_path: Path) -> None:
    allowed_root = tmp_path / "inputs"
    artifact_root = tmp_path / "artifacts"
    allowed_root.mkdir()

    app = build_basic_host_app(
        allowed_roots=[allowed_root],
        artifact_root=artifact_root,
        allowed_origin="http://localhost:8080",
    )

    assert isinstance(app, CORSMiddleware)
    assert app.allow_origins == ["http://localhost:8080"]
    assert app.allow_all_origins is False
    assert app.allow_credentials is False
