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
    image_paths = _write_preview_inputs(images_dir, scenario)
    preview = await _call_tool_json(
        session,
        scenario.get("preview_tool", "render_preview"),
        {
            "request": {
                "input_paths": [str(path) for path in image_paths],
                "pipeline": pipeline,
                "variants_per_image": scenario.get("variants_per_image", 1),
                "seed": scenario.get("seed", 137),
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
    if "summary" not in manifest:
        raise AssertionError(f"{scenario['name']} manifest has no summary: {manifest}")
    if scenario.get("compare_preview"):
        await _run_preview_comparison(session, scenario, image_paths, pipeline, run_id)
    deleted = await _call_tool_json(session, "delete_preview_run", {"run_id": run_id})
    if deleted["deleted"]["run_id"] != run_id:
        raise AssertionError(f"{scenario['name']} did not delete the preview run")


def _write_preview_inputs(images_dir: Path, scenario: dict[str, Any]) -> list[Path]:
    paths: list[Path] = []
    input_count = int(scenario.get("input_count", 1))
    for index in range(input_count):
        image_path = images_dir / f"{scenario['name']}-{index}.png"
        Image.fromarray(np.full((32, 32, 3), 180 + index, dtype=np.uint8)).save(image_path)
        paths.append(image_path)
    return paths


async def _run_preview_comparison(
    session: ClientSession,
    scenario: dict[str, Any],
    image_paths: list[Path],
    pipeline: dict[str, Any],
    baseline_run_id: str,
) -> None:
    candidate_pipeline = await _call_tool_json(
        session,
        "adjust_pipeline",
        {"pipeline": pipeline, "feedback_tags": scenario.get("feedback_tags", ["too_noisy"])},
    )
    candidate = await _call_tool_json(
        session,
        "render_preview_batch",
        {
            "request": {
                "input_paths": [str(path) for path in image_paths],
                "pipeline": candidate_pipeline,
                "variants_per_image": scenario.get("variants_per_image", 1),
                "seed": int(scenario.get("seed", 137)) + 10,
                "max_side": 128,
            },
        },
    )
    comparison = await _call_tool_json(
        session,
        "compare_preview_runs",
        {"baseline_run_id": baseline_run_id, "candidate_run_id": candidate["run_id"]},
    )
    if comparison["baseline"]["run_id"] != baseline_run_id:
        raise AssertionError(f"{scenario['name']} comparison returned wrong baseline: {comparison}")
    if comparison["candidate"]["run_id"] != candidate["run_id"]:
        raise AssertionError(f"{scenario['name']} comparison returned wrong candidate: {comparison}")
    if not comparison["review_notes"]:
        raise AssertionError(f"{scenario['name']} comparison returned no review notes")
    if scenario.get("assert_quality_summary") and not comparison.get("quality_summary"):
        raise AssertionError(f"{scenario['name']} comparison returned no quality summary: {comparison}")
    if scenario.get("summarize_tuning_session"):
        summary = await _call_tool_json(
            session,
            "summarize_tuning_session",
            {
                "baseline_run_id": baseline_run_id,
                "candidate_run_id": candidate["run_id"],
                "feedback_tags": scenario.get("feedback_tags", []),
                "accepted": bool(scenario.get("accepted", False)),
            },
        )
        if summary["candidate_run_id"] != candidate["run_id"]:
            raise AssertionError(f"{scenario['name']} summary returned wrong candidate: {summary}")
        if scenario.get("accepted") and summary["export_ready"] is not True:
            raise AssertionError(f"{scenario['name']} summary was not export-ready: {summary}")
    if scenario.get("record_tuning_decision"):
        decision = await _call_tool_json(
            session,
            "record_tuning_decision",
            {
                "baseline_run_id": baseline_run_id,
                "candidate_run_id": candidate["run_id"],
                "feedback_tags": scenario.get("feedback_tags", []),
                "accepted": bool(scenario.get("accepted", False)),
                "reviewer_notes": ["golden eval accepted candidate"],
            },
        )
        if decision["candidate_run_id"] != candidate["run_id"]:
            raise AssertionError(f"{scenario['name']} decision returned wrong candidate: {decision}")
        decisions = await _call_tool_json(
            session,
            "list_tuning_decisions",
            {"limit": 5, "accepted_only": bool(scenario.get("accepted", False)), "ranked": True},
        )
        if decision["decision_id"] not in {item["decision_id"] for item in decisions["decisions"]}:
            raise AssertionError(f"{scenario['name']} decision was not listed: {decisions}")
    deleted = await _call_tool_json(session, "delete_preview_run", {"run_id": candidate["run_id"]})
    if deleted["deleted"]["run_id"] != candidate["run_id"]:
        raise AssertionError(f"{scenario['name']} did not delete candidate preview run")


async def _call_tool_json(session: ClientSession, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    result = await session.call_tool(name, arguments)
    if result.isError:
        raise AssertionError(f"{name} returned MCP error: {result.content}")
    if result.structuredContent is not None:
        return result.structuredContent
    for content in result.content:
        if getattr(content, "type", None) == "text":
            text = getattr(content, "text", None)
            if isinstance(text, str):
                return json.loads(text)
    raise AssertionError(f"{name} returned no JSON content: {result.content}")


if __name__ == "__main__":
    main()
