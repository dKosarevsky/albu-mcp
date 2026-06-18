from pathlib import Path

import pytest

from albumentationsx_mcp.preview import PathPolicy


def test_path_policy_accepts_files_inside_allowed_root(tmp_path: Path) -> None:
    image_path = tmp_path / "image.png"
    image_path.write_bytes(b"fake")
    policy = PathPolicy(allowed_roots=[tmp_path])

    assert policy.resolve_input(image_path) == image_path.resolve()


def test_path_policy_rejects_files_outside_allowed_root(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside" / "image.png"
    allowed.mkdir()
    outside.parent.mkdir()
    outside.write_bytes(b"fake")
    policy = PathPolicy(allowed_roots=[allowed])

    with pytest.raises(ValueError, match="outside allowed roots"):
        policy.resolve_input(outside)


def test_path_policy_rejects_directories_inside_allowed_root(tmp_path: Path) -> None:
    image_dir = tmp_path / "image-dir"
    image_dir.mkdir()
    policy = PathPolicy(allowed_roots=[tmp_path])

    with pytest.raises(ValueError, match="not a file"):
        policy.resolve_input(image_dir)


def test_path_policy_rejects_symlink_inside_root_to_outside_file(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside" / "image.png"
    allowed.mkdir()
    outside.parent.mkdir()
    outside.write_bytes(b"fake")
    symlink_path = allowed / "linked-outside.png"
    symlink_path.symlink_to(outside)
    policy = PathPolicy(allowed_roots=[allowed])

    with pytest.raises(ValueError, match="outside allowed roots"):
        policy.resolve_input(symlink_path)
