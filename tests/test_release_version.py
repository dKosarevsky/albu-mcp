import pytest

from scripts.check_release_version import validate_release_versions


def write_release_files(tmp_path, *, pyproject_version: str, server_version: str, package_version: str) -> tuple:
    pyproject_path = tmp_path / "pyproject.toml"
    server_json_path = tmp_path / "server.json"
    pyproject_path.write_text(
        f"""
[project]
name = "albumentationsx-mcp"
version = "{pyproject_version}"
""".strip(),
        encoding="utf-8",
    )
    server_json_path.write_text(
        f"""
{{
  "version": "{server_version}",
  "packages": [
    {{
      "registryType": "pypi",
      "identifier": "albumentationsx-mcp",
      "version": "{package_version}"
    }}
  ]
}}
""".strip(),
        encoding="utf-8",
    )
    return pyproject_path, server_json_path


def test_release_version_guard_accepts_matching_versions(tmp_path) -> None:
    pyproject_path, server_json_path = write_release_files(
        tmp_path,
        pyproject_version="0.1.0",
        server_version="0.1.0",
        package_version="0.1.0",
    )

    report = validate_release_versions(
        "v0.1.0",
        pyproject_path=pyproject_path,
        server_json_path=server_json_path,
    )

    assert report.version == "0.1.0"
    assert report.pyproject_version == "0.1.0"
    assert report.server_version == "0.1.0"
    assert report.package_version == "0.1.0"


@pytest.mark.parametrize(
    "case",
    [
        ("0.1.0", "0.1.0", "0.1.0", "0.1.0", "tag must start with 'v'"),
        ("v0.2.0", "0.1.0", "0.1.0", "0.1.0", "pyproject.toml version"),
        ("v0.1.0", "0.1.0", "0.2.0", "0.1.0", "server.json version"),
        ("v0.1.0", "0.1.0", "0.1.0", "0.2.0", "server.json package version"),
    ],
)
def test_release_version_guard_rejects_mismatches(
    tmp_path,
    case,
) -> None:
    tag, pyproject_version, server_version, package_version, message = case
    pyproject_path, server_json_path = write_release_files(
        tmp_path,
        pyproject_version=pyproject_version,
        server_version=server_version,
        package_version=package_version,
    )

    with pytest.raises(ValueError, match=message):
        validate_release_versions(
            tag,
            pyproject_path=pyproject_path,
            server_json_path=server_json_path,
        )
