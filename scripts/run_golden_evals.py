"""Run golden MCP scenarios against the AlbumentationsX MCP stdio server."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from PIL import Image


def main() -> None:
    """Run configured golden scenarios and exit non-zero on the first failure."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario-file", type=Path, default=Path("evals/golden_mcp_scenarios.yaml"))
    parser.add_argument("--work-dir", type=Path, default=Path(".golden-evals"))
    args = parser.parse_args()
    results = asyncio.run(run_scenarios(args.scenario_file, args.work_dir))
    for scenario_name in results:
        sys.stdout.write(f"{scenario_name}: ok\n")


async def run_scenarios(scenario_file: Path, work_dir: Path) -> list[str]:
    """Run all scenarios from a YAML file through an MCP stdio client."""
    scenarios = _load_scenarios(scenario_file)
    images_dir, artifacts_dir = _prepare_work_dirs(work_dir)
    env = dict(os.environ)
    src_path = str(Path.cwd() / "src")
    env["PYTHONPATH"] = f"{src_path}{os.pathsep}{env['PYTHONPATH']}" if env.get("PYTHONPATH") else src_path
    params = StdioServerParameters(
        command=sys.executable,
        args=[
            "-m",
            "albumentationsx_mcp",
            "--allowed-root",
            str(images_dir),
            "--artifact-root",
            str(artifacts_dir),
        ],
        cwd=str(Path.cwd()),
        env=env,
    )

    completed: list[str] = []
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        for scenario in scenarios:
            await _run_scenario(session, scenario, images_dir)
            completed.append(str(scenario["name"]))
    return completed


def _load_scenarios(scenario_file: Path) -> list[dict[str, Any]]:
    payload = yaml.safe_load(scenario_file.read_text(encoding="utf-8"))
    return list(payload["scenarios"])


def _prepare_work_dirs(work_dir: Path) -> tuple[Path, Path]:
    work_dir.mkdir(parents=True, exist_ok=True)
    images_dir = work_dir / "images"
    artifacts_dir = work_dir / "artifacts"
    images_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    return images_dir, artifacts_dir


async def _run_scenario(session: ClientSession, scenario: dict[str, Any], images_dir: Path) -> None:
    task = scenario["task"]
    targets = scenario["targets"]
    recommended = await _call_tool_json(
        session,
        "recommend_pipeline",
        {
            "task": task,
            "intensity": scenario.get("intensity", "medium"),
            "targets": targets,
        },
    )
    pipeline = recommended
    validation = await _call_tool_json(
        session, "validate_pipeline", {"pipeline": pipeline, "target": {"targets": targets}}
    )
    if validation["valid"] is not True:
        raise AssertionError(f"{scenario['name']} validation failed: {validation}")
    explanation = await _call_tool_json(
        session, "explain_pipeline", {"pipeline": pipeline, "target": {"targets": targets}}
    )
    if explanation["risk_level"] not in {"low", "medium", "high"}:
        raise AssertionError(f"{scenario['name']} invalid risk level: {explanation}")
    exported = await _call_tool_json(
        session,
        "export_pipeline",
        {"pipeline": pipeline, "output_format": scenario.get("export_format", "json")},
    )
    if not exported["content"]:
        raise AssertionError(f"{scenario['name']} produced an empty export")

    if scenario.get("preview"):
        await _run_preview_lifecycle(session, scenario, images_dir, pipeline)


async def _run_preview_lifecycle(
    session: ClientSession,
    scenario: dict[str, Any],
    images_dir: Path,
    pipeline: dict[str, Any],
) -> None:
    image_path = images_dir / f"{scenario['name']}.png"
    Image.fromarray(np.full((32, 32, 3), 180, dtype=np.uint8)).save(image_path)
    preview = await _call_tool_json(
        session,
        "render_preview",
        {
            "request": {
                "input_paths": [str(image_path)],
                "pipeline": pipeline,
                "variants_per_image": scenario.get("variants_per_image", 1),
                "max_side": 128,
            },
        },
    )
    run_id = preview["run_id"]
    runs = await _call_tool_json(session, "list_preview_runs", {"limit": 5})
    if run_id not in {run["run_id"] for run in runs["runs"]}:
        raise AssertionError(f"{scenario['name']} preview run was not indexed")
    manifest = await _call_tool_json(session, "get_preview_manifest", {"run_id": run_id})
    if manifest["run_id"] != run_id:
        raise AssertionError(f"{scenario['name']} returned wrong manifest: {manifest}")
    deleted = await _call_tool_json(session, "delete_preview_run", {"run_id": run_id})
    if deleted["deleted"]["run_id"] != run_id:
        raise AssertionError(f"{scenario['name']} did not delete the preview run")


async def _call_tool_json(session: ClientSession, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    result = await session.call_tool(name, arguments)
    if result.isError:
        raise AssertionError(f"{name} returned MCP error: {result.content}")
    if result.structuredContent is not None:
        return result.structuredContent
    for content in result.content:
        if getattr(content, "type", None) == "text":
            return json.loads(content.text)
    raise AssertionError(f"{name} returned no JSON content: {result.content}")


if __name__ == "__main__":
    main()
