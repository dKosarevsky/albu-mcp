"""Export a deterministic snapshot of the public argparse contract."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import patch

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from albumentationsx_mcp import cli

CliRunner = Callable[[list[str]], None]

_GROUP_RUNNERS: dict[str, CliRunner] = {
    "activation": cli._run_activation_cli,  # noqa: SLF001
    "beta": cli._run_beta_cli,  # noqa: SLF001
    "distribution": cli._run_distribution_cli,  # noqa: SLF001
    "evidence": cli._run_evidence_cli,  # noqa: SLF001
    "host": cli._run_host_cli,  # noqa: SLF001
    "intake": cli._run_intake_cli,  # noqa: SLF001
    "preview": cli._run_preview_cli,  # noqa: SLF001
    "rc": cli._run_rc_cli,  # noqa: SLF001
    "trust": cli._run_trust_cli,  # noqa: SLF001
}


class _ParserCapturedSignal(BaseException):
    def __init__(self, parser: argparse.ArgumentParser) -> None:
        super().__init__()
        self.parser = parser


def build_cli_contract_snapshot() -> dict[str, Any]:
    """Return the canonical server and grouped CLI parser contract."""
    groups = sorted(cli._SUBCOMMANDS)  # noqa: SLF001
    if groups != sorted(_GROUP_RUNNERS):
        message = "CLI dispatcher groups do not match contract exporter runners"
        raise RuntimeError(message)
    return {
        "console_scripts": ["albumentationsx-mcp", "albu-mcp"],
        "dispatch": {
            "default": "server",
            "groups": groups,
        },
        "server": _parser_entry(_capture_parser(cli._run_server)),  # noqa: SLF001
        "groups": {name: _parser_entry(_capture_parser(_GROUP_RUNNERS[name])) for name in groups},
    }


def dump_cli_contract_snapshot(snapshot: dict[str, Any]) -> str:
    """Serialize a CLI contract snapshot with stable formatting."""
    return json.dumps(_json_safe(snapshot), indent=2, sort_keys=True) + "\n"


def main() -> None:
    """Write the current CLI contract snapshot to stdout or a file."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional path to write the snapshot JSON.")
    args = parser.parse_args()

    content = dump_cli_contract_snapshot(build_cli_contract_snapshot())
    if args.output is None:
        sys.stdout.write(content)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")


def _capture_parser(runner: CliRunner) -> argparse.ArgumentParser:
    def capture(
        parser: argparse.ArgumentParser,
        args: list[str] | None = None,
        namespace: argparse.Namespace | None = None,
    ) -> argparse.Namespace:
        del args, namespace
        raise _ParserCapturedSignal(parser)

    with patch.object(argparse.ArgumentParser, "parse_args", capture):
        try:
            runner([])
        except _ParserCapturedSignal as signal:
            return signal.parser
    message = "CLI runner did not parse arguments"
    raise RuntimeError(message)


def _parser_entry(parser: argparse.ArgumentParser) -> dict[str, Any]:
    subparsers = _subparser_action(parser)
    return {
        "description": parser.description,
        "options": [_action_entry(action) for action in parser._actions if _is_authored_option(action)],  # noqa: SLF001
        "command_dest": subparsers.dest if subparsers is not None else None,
        "command_required": subparsers.required if subparsers is not None else False,
        "commands": _command_entries(subparsers) if subparsers is not None else {},
    }


def _subparser_action(parser: argparse.ArgumentParser) -> Any | None:
    return next(
        (action for action in parser._actions if type(action).__name__ == "_SubParsersAction"),  # noqa: SLF001
        None,
    )


def _is_authored_option(action: argparse.Action) -> bool:
    return type(action).__name__ not in {"_HelpAction", "_SubParsersAction"}


def _action_entry(action: argparse.Action) -> dict[str, Any]:
    choices = list(action.choices) if action.choices is not None else None
    return {
        "flags": list(action.option_strings),
        "dest": action.dest,
        "action": type(action).__name__,
        "required": action.required,
        "nargs": action.nargs,
        "choices": _json_safe(choices),
        "default": _json_safe(action.default),
        "const": _json_safe(action.const),
        "type": _type_name(action.type),
        "metavar": _json_safe(action.metavar),
        "help": action.help,
    }


def _command_entries(subparsers: Any) -> dict[str, Any]:
    help_by_name = {
        choice.dest: choice.help
        for choice in subparsers._choices_actions  # noqa: SLF001
    }
    return {
        name: {
            "help": help_by_name.get(name),
            **_parser_entry(parser),
        }
        for name, parser in subparsers.choices.items()
    }


def _type_name(value: Any) -> str | None:
    if value is None:
        return None
    return getattr(value, "__name__", type(value).__name__)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
