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
from pydantic import AnyUrl

_RANKING_CANDIDATE_COUNT = 2


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
    if scenario.get("client_smoke"):
        await _run_client_smoke(session, scenario)
    if scenario.get("diagnostics_smoke"):
        await _run_diagnostics_smoke(session, scenario)
    if scenario.get("recommend_recipe"):
        await _run_recipe_recommendation(session, scenario)
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
    quality_profile = scenario.get("quality_profile", "balanced")
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
        {
            "baseline_run_id": baseline_run_id,
            "candidate_run_id": candidate["run_id"],
            "quality_profile": quality_profile,
        },
    )
    if comparison["baseline"]["run_id"] != baseline_run_id:
        raise AssertionError(f"{scenario['name']} comparison returned wrong baseline: {comparison}")
    if comparison["candidate"]["run_id"] != candidate["run_id"]:
        raise AssertionError(f"{scenario['name']} comparison returned wrong candidate: {comparison}")
    if not comparison["review_notes"]:
        raise AssertionError(f"{scenario['name']} comparison returned no review notes")
    if scenario.get("assert_quality_summary") and not comparison.get("quality_summary"):
        raise AssertionError(f"{scenario['name']} comparison returned no quality summary: {comparison}")
    if scenario.get("record_preview_feedback"):
        await _run_preview_feedback_loop(session, scenario, candidate["run_id"], candidate_pipeline)
    if scenario.get("summarize_tuning_session"):
        summary = await _call_tool_json(
            session,
            "summarize_tuning_session",
            {
                "baseline_run_id": baseline_run_id,
                "candidate_run_id": candidate["run_id"],
                "feedback_tags": scenario.get("feedback_tags", []),
                "accepted": bool(scenario.get("accepted", False)),
                "quality_profile": quality_profile,
            },
        )
        if summary["candidate_run_id"] != candidate["run_id"]:
            raise AssertionError(f"{scenario['name']} summary returned wrong candidate: {summary}")
        if scenario.get("accepted") and summary["export_ready"] is not True:
            raise AssertionError(f"{scenario['name']} summary was not export-ready: {summary}")
    extra_candidate_ids = await _run_candidate_ranking(
        session,
        scenario,
        image_paths,
        pipeline,
        baseline_run_id,
        candidate["run_id"],
        quality_profile,
    )
    candidate_ids = [candidate["run_id"], *extra_candidate_ids]
    await _record_tuning_decision_and_report(
        session,
        scenario,
        baseline_run_id,
        candidate["run_id"],
        quality_profile,
    )
    await _run_dataset_scoring_and_preview_report(
        session,
        scenario,
        baseline_run_id,
        candidate_ids,
        quality_profile,
    )
    for extra_candidate_id in extra_candidate_ids:
        deleted_extra = await _call_tool_json(session, "delete_preview_run", {"run_id": extra_candidate_id})
        if deleted_extra["deleted"]["run_id"] != extra_candidate_id:
            raise AssertionError(f"{scenario['name']} did not delete extra candidate run")
    deleted = await _call_tool_json(session, "delete_preview_run", {"run_id": candidate["run_id"]})
    if deleted["deleted"]["run_id"] != candidate["run_id"]:
        raise AssertionError(f"{scenario['name']} did not delete candidate preview run")


async def _run_candidate_ranking(  # noqa: PLR0913
    session: ClientSession,
    scenario: dict[str, Any],
    image_paths: list[Path],
    pipeline: dict[str, Any],
    baseline_run_id: str,
    candidate_run_id: str,
    quality_profile: str,
) -> list[str]:
    if not scenario.get("rank_preview_candidates"):
        return []
    alternate_tags = scenario.get("alternate_feedback_tags", ["too_blurry"])
    alternate_pipeline = await _call_tool_json(
        session,
        "adjust_pipeline",
        {"pipeline": pipeline, "feedback_tags": alternate_tags},
    )
    alternate = await _call_tool_json(
        session,
        "render_preview_batch",
        {
            "request": {
                "input_paths": [str(path) for path in image_paths],
                "pipeline": alternate_pipeline,
                "variants_per_image": scenario.get("variants_per_image", 1),
                "seed": int(scenario.get("seed", 137)) + 20,
                "max_side": 128,
            },
        },
    )
    ranking = await _call_tool_json(
        session,
        "rank_preview_candidates",
        {
            "baseline_run_id": baseline_run_id,
            "candidate_run_ids": [candidate_run_id, alternate["run_id"]],
            "feedback_tags_by_candidate": {
                candidate_run_id: scenario.get("feedback_tags", []),
                alternate["run_id"]: alternate_tags,
            },
            "accepted_candidate_ids": [candidate_run_id] if scenario.get("accepted") else [],
            "quality_profile": quality_profile,
        },
    )
    if ranking["candidate_count"] != _RANKING_CANDIDATE_COUNT:
        raise AssertionError(f"{scenario['name']} ranking did not include both candidates: {ranking}")
    if not ranking["best_candidate_run_id"]:
        raise AssertionError(f"{scenario['name']} ranking did not return a best candidate: {ranking}")
    return [str(alternate["run_id"])]


async def _run_preview_feedback_loop(
    session: ClientSession,
    scenario: dict[str, Any],
    candidate_run_id: str,
    candidate_pipeline: dict[str, Any],
) -> None:
    feedback_tags = scenario.get("preview_feedback_tags", scenario.get("feedback_tags", []))
    image_index = int(scenario.get("feedback_image_index", 0))
    variant_index = int(scenario.get("feedback_variant_index", 0))
    feedback = await _call_tool_json(
        session,
        "record_preview_feedback",
        {
            "run_id": candidate_run_id,
            "image_index": image_index,
            "variant_index": variant_index,
            "feedback_tags": feedback_tags,
            "note": scenario.get("preview_feedback_note", ""),
            "accepted": bool(scenario.get("preview_feedback_accepted", False)),
        },
    )
    expected_target = f"example {image_index + 1} / variant {variant_index + 1}"
    if feedback["review_target"] != expected_target:
        raise AssertionError(f"{scenario['name']} feedback returned wrong target: {feedback}")
    if feedback["recommended_next_tool"] != "adjust_pipeline":
        raise AssertionError(f"{scenario['name']} feedback returned wrong next tool: {feedback}")
    listed = await _call_tool_json(
        session,
        "list_preview_feedback",
        {"run_id": candidate_run_id, "limit": 5},
    )
    if feedback["feedback_id"] not in {item["feedback_id"] for item in listed["feedback"]}:
        raise AssertionError(f"{scenario['name']} feedback was not listed: {listed}")
    for tag in feedback_tags:
        if tag not in listed["aggregated_feedback_tags"]:
            raise AssertionError(f"{scenario['name']} feedback tag was not aggregated: {listed}")
    adjusted = await _call_tool_json(
        session,
        "adjust_pipeline",
        {"pipeline": candidate_pipeline, "feedback_tags": listed["aggregated_feedback_tags"]},
    )
    if not adjusted.get("transforms"):
        raise AssertionError(f"{scenario['name']} feedback adjustment returned no transforms: {adjusted}")


async def _run_recipe_recommendation(session: ClientSession, scenario: dict[str, Any]) -> None:
    recipe = await _call_tool_json(
        session,
        "recommend_recipe",
        {
            "task": scenario.get("recipe_task", scenario["task"]),
            "intensity": scenario.get("intensity", "medium"),
            "targets": scenario.get("recipe_targets"),
        },
    )
    expected_profile = scenario.get("expected_recipe_profile")
    if expected_profile and recipe["quality_profile"] != expected_profile:
        raise AssertionError(f"{scenario['name']} recipe returned wrong quality profile: {recipe}")
    if scenario.get("assert_recipe_explanations"):
        explanation_kinds = {item["kind"] for item in recipe.get("explanations", [])}
        expected_kinds = {"quality_profile", "targets", "feedback_tags", "workflow"}
        if explanation_kinds != expected_kinds:
            raise AssertionError(f"{scenario['name']} recipe returned wrong explanations: {recipe}")
        if not all(item.get("rationale") for item in recipe["explanations"]):
            raise AssertionError(f"{scenario['name']} recipe returned empty explanation rationale: {recipe}")
    for tool_name in ("render_preview_batch", "score_dataset_preview_candidates", "export_preview_report"):
        if tool_name not in recipe["recommended_tools"]:
            raise AssertionError(f"{scenario['name']} recipe did not include {tool_name}: {recipe}")


async def _run_client_smoke(session: ClientSession, scenario: dict[str, Any]) -> None:
    smoke_resources = scenario.get("smoke_resources", [])
    expected_resources = {
        "albumentationsx://examples/client-smoke",
        "albumentationsx://capabilities",
        "albumentationsx://recipes/catalog",
    }
    if set(smoke_resources) != expected_resources:
        raise AssertionError(f"{scenario['name']} declares wrong smoke resources: {smoke_resources}")

    playbook = await _read_resource_json(session, "albumentationsx://examples/client-smoke")
    step_tools = [step["tool"] for step in playbook["steps"]]
    expected_steps = [
        "albumentationsx://capabilities",
        "albumentationsx://recipes/catalog",
        "recommend_recipe",
        "validate_pipeline",
    ]
    if playbook["trigger_phrase"] != "is AlbumentationsX MCP connected?":
        raise AssertionError(f"{scenario['name']} returned wrong smoke trigger phrase: {playbook}")
    if step_tools != expected_steps:
        raise AssertionError(f"{scenario['name']} returned wrong smoke step tools: {playbook}")

    capabilities = await _read_resource_json(session, "albumentationsx://capabilities")
    for resource_uri in ("albumentationsx://examples/client-smoke", "albumentationsx://recipes/catalog"):
        if resource_uri not in capabilities["workflow_resources"]:
            raise AssertionError(f"{scenario['name']} capabilities did not include {resource_uri}: {capabilities}")
    for tool_name in ("recommend_recipe", "validate_pipeline"):
        if tool_name not in capabilities["tools"]:
            raise AssertionError(f"{scenario['name']} capabilities did not include {tool_name}: {capabilities}")

    recipes = await _read_resource_json(session, "albumentationsx://recipes/catalog")
    if "classification" not in {recipe["name"] for recipe in recipes}:
        raise AssertionError(f"{scenario['name']} recipes catalog did not include classification: {recipes}")

    recipe = await _call_tool_json(
        session,
        "recommend_recipe",
        {
            "task": scenario["task"],
            "intensity": scenario.get("intensity", "medium"),
            "targets": scenario["targets"],
        },
    )
    if recipe["quality_profile"] != "classification":
        raise AssertionError(f"{scenario['name']} recipe returned wrong quality profile: {recipe}")
    validation = await _call_tool_json(
        session,
        "validate_pipeline",
        {"pipeline": recipe["pipeline"], "target": {"targets": scenario["targets"]}},
    )
    if validation["valid"] is not True:
        raise AssertionError(f"{scenario['name']} smoke validation failed: {validation}")


async def _run_diagnostics_smoke(session: ClientSession, scenario: dict[str, Any]) -> None:
    diagnostics_resources = scenario.get("diagnostics_resources", [])
    expected_resources = {
        "albumentationsx://diagnostics/guide",
        "albumentationsx://capabilities",
    }
    if set(diagnostics_resources) != expected_resources:
        raise AssertionError(f"{scenario['name']} declares wrong diagnostics resources: {diagnostics_resources}")

    guide = await _read_resource_json(session, "albumentationsx://diagnostics/guide")
    step_tools = [step["tool"] for step in guide["steps"]]
    expected_steps = [
        "albumentationsx://diagnostics/guide",
        "diagnose_environment",
        "albumentationsx://capabilities",
    ]
    if guide["trigger_phrase"] != "why does AlbumentationsX MCP preview not work?":
        raise AssertionError(f"{scenario['name']} returned wrong diagnostics trigger phrase: {guide}")
    if step_tools != expected_steps:
        raise AssertionError(f"{scenario['name']} returned wrong diagnostics step tools: {guide}")

    capabilities = await _read_resource_json(session, "albumentationsx://capabilities")
    for resource_uri in ("albumentationsx://diagnostics/guide", "albumentationsx://examples/diagnostics"):
        if resource_uri not in capabilities["workflow_resources"]:
            raise AssertionError(f"{scenario['name']} capabilities did not include {resource_uri}: {capabilities}")
    if "diagnose_environment" not in capabilities["tools"]:
        raise AssertionError(f"{scenario['name']} capabilities did not include diagnose_environment: {capabilities}")

    report = await _call_tool_json(session, "diagnose_environment", {"include_write_probe": True})
    if report["status"] != "ok":
        raise AssertionError(f"{scenario['name']} diagnostics report was not ok: {report}")
    check_codes = {check["code"] for check in report["checks"]}
    expected_check_codes = {
        "albumentationsx_import",
        "allowed_root_accessible",
        "artifact_root_accessible",
        "artifact_root_write_probe",
        "required_tools_available",
        "required_prompts_available",
        "required_workflow_resources_available",
    }
    if not expected_check_codes.issubset(check_codes):
        raise AssertionError(f"{scenario['name']} diagnostics missed expected checks: {report}")
    if report["environment"]["write_probe"] != "passed":
        raise AssertionError(f"{scenario['name']} diagnostics write probe did not pass: {report}")
    if not report["next_actions"]:
        raise AssertionError(f"{scenario['name']} diagnostics returned no next actions: {report}")


async def _run_dataset_scoring_and_preview_report(
    session: ClientSession,
    scenario: dict[str, Any],
    baseline_run_id: str,
    candidate_run_ids: list[str],
    quality_profile: str,
) -> None:
    score: dict[str, Any] | None = None
    if scenario.get("score_dataset_preview_candidates"):
        score = await _call_tool_json(
            session,
            "score_dataset_preview_candidates",
            {
                "baseline_run_id": baseline_run_id,
                "candidate_run_ids": candidate_run_ids,
                "feedback_tags_by_candidate": {candidate_run_ids[0]: scenario.get("feedback_tags", [])},
                "accepted_candidate_ids": [candidate_run_ids[0]] if scenario.get("accepted") else [],
                "quality_profile": quality_profile,
            },
        )
        if score["candidate_count"] != len(candidate_run_ids):
            raise AssertionError(f"{scenario['name']} dataset score did not include all candidates: {score}")
        if not score["best_candidate_run_id"]:
            raise AssertionError(f"{scenario['name']} dataset score did not return a best candidate: {score}")
        if not score["metric_stats"]:
            raise AssertionError(f"{scenario['name']} dataset score returned no metric stats: {score}")
    if scenario.get("export_preview_report"):
        report = await _call_tool_json(
            session,
            "export_preview_report",
            {
                "baseline_run_id": baseline_run_id,
                "candidate_run_ids": candidate_run_ids,
                "output_format": scenario.get("preview_report_format", "markdown"),
                "feedback_tags_by_candidate": {candidate_run_ids[0]: scenario.get("feedback_tags", [])},
                "accepted_candidate_ids": [candidate_run_ids[0]] if scenario.get("accepted") else [],
                "quality_profile": quality_profile,
                "include_decisions": True,
            },
        )
        if report["artifact"]["kind"] != "report":
            raise AssertionError(f"{scenario['name']} preview report returned wrong artifact: {report}")
        report_exists = await asyncio.to_thread(Path(report["artifact"]["path"]).exists)
        if not report_exists:
            raise AssertionError(f"{scenario['name']} preview report artifact was not written: {report}")
        if score is not None and score["best_candidate_run_id"] not in report["content"]:
            raise AssertionError(f"{scenario['name']} preview report did not include best candidate: {report}")
        if scenario.get("assert_preview_report_images"):
            expected_markup = _expected_report_image_markup(scenario.get("preview_report_format", "markdown"))
            if expected_markup not in report["content"]:
                raise AssertionError(f"{scenario['name']} preview report did not include image markup: {report}")
        if scenario.get("assert_preview_report_feedback"):
            _assert_preview_report_feedback(scenario, report["content"])


def _expected_report_image_markup(output_format: str) -> str:
    if output_format == "html":
        return '<img class="contact-sheet"'
    return "![contact sheet]"


def _assert_preview_report_feedback(scenario: dict[str, Any], content: str) -> None:
    image_index = int(scenario.get("feedback_image_index", 0))
    variant_index = int(scenario.get("feedback_variant_index", 0))
    expected_values = [
        "Concrete Preview Feedback",
        f"example {image_index + 1} / variant {variant_index + 1}",
        scenario.get("preview_feedback_note", ""),
        *scenario.get("preview_feedback_tags", scenario.get("feedback_tags", [])),
    ]
    missing_values = [str(value) for value in expected_values if value and str(value) not in content]
    if missing_values:
        raise AssertionError(
            f"{scenario['name']} preview report did not include recorded feedback values: {missing_values}"
        )


async def _record_tuning_decision_and_report(
    session: ClientSession,
    scenario: dict[str, Any],
    baseline_run_id: str,
    candidate_run_id: str,
    quality_profile: str,
) -> None:
    if not scenario.get("record_tuning_decision"):
        return
    decision = await _call_tool_json(
        session,
        "record_tuning_decision",
        {
            "baseline_run_id": baseline_run_id,
            "candidate_run_id": candidate_run_id,
            "feedback_tags": scenario.get("feedback_tags", []),
            "accepted": bool(scenario.get("accepted", False)),
            "reviewer_notes": ["golden eval accepted candidate"],
            "quality_profile": quality_profile,
        },
    )
    if decision["candidate_run_id"] != candidate_run_id:
        raise AssertionError(f"{scenario['name']} decision returned wrong candidate: {decision}")
    decisions = await _call_tool_json(
        session,
        "list_tuning_decisions",
        {"limit": 5, "accepted_only": bool(scenario.get("accepted", False)), "ranked": True},
    )
    if decision["decision_id"] not in {item["decision_id"] for item in decisions["decisions"]}:
        raise AssertionError(f"{scenario['name']} decision was not listed: {decisions}")
    if scenario.get("export_tuning_report"):
        report = await _call_tool_json(
            session,
            "export_tuning_report",
            {"output_format": "json", "limit": 10, "accepted_only": False, "ranked": True},
        )
        if decision["decision_id"] not in report["content"]:
            raise AssertionError(f"{scenario['name']} report did not include decision: {report}")


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


async def _read_resource_json(session: ClientSession, uri: str) -> Any:
    result = await session.read_resource(AnyUrl(uri))
    for content in result.contents:
        text = getattr(content, "text", None)
        if isinstance(text, str):
            return json.loads(text)
    raise AssertionError(f"{uri} returned no JSON text content: {result.contents}")


if __name__ == "__main__":
    main()
