from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path

import pytest

_SOURCE_ROOT = Path("src")
_PACKAGE_ROOT = _SOURCE_ROOT / "albumentationsx_mcp"
_TRANSPORT_BOUNDARIES = {
    _PACKAGE_ROOT / "cli.py",
    _PACKAGE_ROOT / "server.py",
}
_FORBIDDEN_DOMAIN_IMPORTS = (
    "albumentationsx_mcp.adapters",
    "argparse",
    "mcp.server.fastmcp",
)
_CLI_COMPOSITION_MODULES = {
    "__init__.py",
    "app.py",
    "contracts.py",
    "evidence.py",
    "registration.py",
}


def _module_name(path: Path) -> tuple[str, ...]:
    parts = path.relative_to(_SOURCE_ROOT).with_suffix("").parts
    return parts[:-1] if parts[-1] == "__init__" else parts


def _imported_modules(path: Path) -> Iterator[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    current_package = _module_name(path)[:-1] if path.name != "__init__.py" else _module_name(path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                if node.module is not None:
                    yield node.lineno, node.module
                continue
            base = current_package[: len(current_package) - node.level + 1]
            if node.module is not None:
                yield node.lineno, ".".join((*base, node.module))
            else:
                for alias in node.names:
                    yield node.lineno, ".".join((*base, alias.name))


def _is_forbidden_domain_import(module: str) -> bool:
    return any(module == prefix or module.startswith(f"{prefix}.") for prefix in _FORBIDDEN_DOMAIN_IMPORTS)


def test_domain_modules_do_not_depend_on_transport_adapters() -> None:
    violations: list[str] = []
    for path in sorted(_PACKAGE_ROOT.rglob("*.py")):
        if path in _TRANSPORT_BOUNDARIES or "adapters" in path.relative_to(_PACKAGE_ROOT).parts:
            continue
        for line, module in _imported_modules(path):
            if _is_forbidden_domain_import(module):
                violations.append(f"{path}:{line} imports {module}")

    assert violations == [], "domain-to-transport dependency violations:\n" + "\n".join(violations)


@pytest.mark.parametrize(
    ("path", "line_limit"),
    [
        (_PACKAGE_ROOT / "cli.py", 120),
        *(
            (path, 250 if path.name in _CLI_COMPOSITION_MODULES else 700)
            for path in sorted((_PACKAGE_ROOT / "adapters" / "cli").glob("*.py"))
        ),
    ],
    ids=lambda value: str(value.relative_to(_PACKAGE_ROOT)) if isinstance(value, Path) else str(value),
)
def test_cli_transport_modules_stay_within_size_budget(path: Path, line_limit: int) -> None:
    line_count = len(path.read_text(encoding="utf-8").splitlines())

    assert line_count <= line_limit, f"{path} has {line_count} lines; architecture budget is {line_limit}"
