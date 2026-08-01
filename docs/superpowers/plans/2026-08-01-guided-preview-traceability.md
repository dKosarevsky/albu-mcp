# Guided First Preview And Variant Traceability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one bounded `run_first_preview` use case and exact, manifest-backed `trace_preview_variant` inspection for newly rendered AlbumentationsX previews.

**Architecture:** A transport-independent `GuidedPreviewService` composes the existing onboarding, validation, and preview services. Applied transform parameters are captured by instrumenting `Compose`, normalized by a bounded trace module, and stored additively in preview manifests; MCP adapters only validate arguments and delegate.

**Tech Stack:** Python 3.10+, AlbumentationsX 2.3.1 `Compose(save_applied_params=True)`, Pydantic v2, FastMCP 1.x, NumPy, Pillow, pytest, Ruff, ty, uv.

---

## File Map

- Create `src/albumentationsx_mcp/preview_trace.py`: typed trace contracts, bounded JSON normalization, trace creation,
  and manifest-backed trace lookup.
- Create `src/albumentationsx_mcp/guided_preview.py`: one application service for onboarding, validation, and first
  rendering.
- Modify `src/albumentationsx_mcp/pipeline.py`: enable applied-parameter capture on runtime pipelines.
- Modify `src/albumentationsx_mcp/preview.py`: attach one trace to every rendered image variant and persist traces in
  manifests.
- Modify `src/albumentationsx_mcp/adapters/mcp/dataset.py`: register `run_first_preview`.
- Modify `src/albumentationsx_mcp/adapters/mcp/preview.py`: register `trace_preview_variant`.
- Modify `src/albumentationsx_mcp/adapters/mcp/dependencies.py`: expose the already-constructed guided service.
- Modify `src/albumentationsx_mcp/adapters/mcp/registration.py`: compose the service and extend the canonical tool list.
- Modify `src/albumentationsx_mcp/server.py`: construct the guided service with profile-aware recipe availability.
- Create `tests/test_preview_trace.py`: serializer and lookup behavior.
- Create `tests/test_guided_preview.py`: success and blocked-gate behavior.
- Modify `tests/test_pipeline.py`, `tests/test_artifacts.py`, and `tests/test_annotation_preview.py`: instrumentation,
  manifest, determinism, and annotation regressions.
- Modify `tests/test_mcp_adapters.py`, `tests/test_mcp_profiles.py`, `tests/test_mcp_stdio.py`, and
  `tests/fixtures/snapshots/mcp_contract.json`: public MCP contract coverage.
- Modify `README.md`, `docs/USAGE.md`, `docs/FIRST_10_MINUTES.md`, `examples/first_10_minutes_prompt.md`,
  `scripts/check_first_10_minutes.py`, and `CHANGELOG.md`: preferred one-call workflow and trace documentation.

### Task 1: Bounded Variant Trace Values

**Files:**
- Create: `src/albumentationsx_mcp/preview_trace.py`
- Create: `tests/test_preview_trace.py`

- [ ] **Step 1: Write failing normalization tests**

Create parameterized tests for JSON primitives, paths, NumPy scalars, small arrays, large arrays, long strings, long
sequences, excessive nesting, exhausted node budgets, and unsupported values:

```python
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        (True, True),
        (3, 3),
        (1.25, 1.25),
        (Path("sample.png"), "sample.png"),
        (np.int64(7), 7),
        (np.array([[1, 2]], dtype=np.int16), [[1, 2]]),
    ],
)
def test_normalize_trace_value_preserves_small_json_values(value: object, expected: object) -> None:
    assert normalize_trace_value(value) == expected


def test_normalize_trace_value_summarizes_large_array() -> None:
    value = np.arange(MAX_INLINE_ARRAY_ELEMENTS + 1, dtype=np.float32)

    result = normalize_trace_value(value)

    assert result["kind"] == "ndarray_summary"
    assert result["shape"] == [MAX_INLINE_ARRAY_ELEMENTS + 1]
    assert result["dtype"] == "float32"
    assert result["element_count"] == MAX_INLINE_ARRAY_ELEMENTS + 1
    assert len(result["sha256"]) == 64
```

Also assert that collections are capped at `MAX_COLLECTION_ITEMS`, recursion is capped at `MAX_TRACE_DEPTH`, non-finite
floats receive an explicit structural representation, and the normalized result survives
`json.dumps(..., allow_nan=False)`.

- [ ] **Step 2: Run the tests and verify the missing module failure**

Run:

```bash
uv run pytest tests/test_preview_trace.py -q
```

Expected: collection fails with `ModuleNotFoundError: No module named 'albumentationsx_mcp.preview_trace'`.

- [ ] **Step 3: Implement typed traces and bounded normalization**

Create these public contracts and constants in `preview_trace.py`:

```python
MAX_INLINE_ARRAY_ELEMENTS = 64
MAX_COLLECTION_ITEMS = 32
MAX_TRACE_DEPTH = 5
MAX_TRACE_NODES = 128
MAX_INLINE_STRING_CHARS = 256
MAX_APPLIED_TRANSFORMS = 32
MAX_VARIANT_TRACE_JSON_BYTES = 8 * 1024


class AppliedTransformTrace(StrictModel):
    name: str
    params: dict[str, Any] = Field(default_factory=dict)


class PreviewVariantTrace(StrictModel):
    image_index: int = Field(ge=0)
    variant_index: int = Field(ge=0)
    source_path: str
    artifact_uri: str
    effective_seed: int | None = None
    applied_transforms: list[AppliedTransformTrace] = Field(default_factory=list)
    truncated_transform_count: int = Field(default=0, ge=0)
    parameters_truncated: bool = False


class PreviewVariantTraceResult(StrictModel):
    run_id: str
    image_index: int = Field(ge=0)
    variant_index: int = Field(ge=0)
    available: bool
    trace: PreviewVariantTrace | None = None
    message: str
```

Implement a private `_TraceNormalizer` with a shared `MAX_TRACE_NODES` budget and expose
`normalize_trace_value(value: Any) -> Any` as a fresh-normalizer facade. Use the following closed behavior inside the
normalizer:

```python
if value is None or isinstance(value, (bool, int)):
    return value
if isinstance(value, str):
    if len(value) <= MAX_INLINE_STRING_CHARS:
        return value
    return {
        "kind": "string_summary",
        "length": len(value),
        "sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
    }
if isinstance(value, float):
    return value if math.isfinite(value) else {"kind": "non_finite_float", "value": str(value)}
if isinstance(value, Path):
    return str(value)
if isinstance(value, np.generic):
    return self.normalize(value.item(), depth=depth)
if isinstance(value, np.ndarray):
    if value.size <= MAX_INLINE_ARRAY_ELEMENTS:
        return self.normalize(value.tolist(), depth=depth + 1)
    contiguous = np.ascontiguousarray(value)
    return {
        "kind": "ndarray_summary",
        "shape": list(value.shape),
        "dtype": str(value.dtype),
        "element_count": int(value.size),
        "sha256": hashlib.sha256(contiguous.tobytes()).hexdigest(),
    }
```

Mappings use sorted, bounded string keys and at most `MAX_COLLECTION_ITEMS` entries. Lists and tuples retain at most
that many normalized entries and include `kind`, `item_count`, and `truncated` metadata when capped. Each visited value
consumes one shared node; once the node budget or `MAX_TRACE_DEPTH` is reached, return only `kind`, Python type name,
and collection length. Unsupported objects return `{"kind": "unsupported", "type": type(value).__qualname__}`
without `repr(value)`.

- [ ] **Step 4: Run focused tests and static checks**

Run:

```bash
uv run pytest tests/test_preview_trace.py -q
uv run ruff check src/albumentationsx_mcp/preview_trace.py tests/test_preview_trace.py
uv run ty check src/albumentationsx_mcp/preview_trace.py tests/test_preview_trace.py
```

Expected: all commands exit `0`.

- [ ] **Step 5: Commit the bounded trace contract**

```bash
git add src/albumentationsx_mcp/preview_trace.py tests/test_preview_trace.py
git commit -m "feat: add bounded preview trace values"
```

### Task 2: Applied Transform Capture And Trace Lookup

**Files:**
- Modify: `src/albumentationsx_mcp/pipeline.py`
- Modify: `src/albumentationsx_mcp/preview.py`
- Modify: `src/albumentationsx_mcp/preview_trace.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_artifacts.py`
- Modify: `tests/test_annotation_preview.py`
- Modify: `tests/test_preview_trace.py`

- [ ] **Step 1: Write failing pipeline instrumentation and manifest tests**

Add a pipeline test that compares an ordinary seeded `A.Compose` with `PipelineService.build_pipeline`:

```python
def test_build_pipeline_records_applied_params_without_changing_seeded_output() -> None:
    image = np.arange(16 * 16 * 3, dtype=np.uint8).reshape((16, 16, 3))
    spec = ComposeSpec(
        transforms=[
            TransformSpec(name="HorizontalFlip", p=1.0),
            TransformSpec(name="GaussNoise", params={"std_range": (0.01, 0.02)}, p=1.0),
        ],
        seed=17,
    )
    expected = A.Compose(
        [A.HorizontalFlip(p=1.0), A.GaussNoise(std_range=(0.01, 0.02), p=1.0)],
        seed=17,
    )(image=image)["image"]

    result = PipelineService(TransformCatalog()).build_pipeline(spec)(image=image)

    assert np.array_equal(result["image"], expected)
    assert [name for name, _ in result["applied_transforms"]] == ["HorizontalFlip", "GaussNoise"]
```

Add an artifact test using the real `PipelineService` and assert one `variant_traces` item per image/variant, ordered
transform names, artifact URI, and exact effective seed. Extend an annotation preview assertion to prove
`annotation_observations` and `variant_traces` coexist.

- [ ] **Step 2: Run tests and verify trace fields are absent**

Run:

```bash
uv run pytest tests/test_pipeline.py::test_build_pipeline_records_applied_params_without_changing_seeded_output \
  tests/test_artifacts.py -q
```

Expected: failures show missing `applied_transforms` or missing `variant_traces`.

- [ ] **Step 3: Enable applied-parameter capture**

Add the single compatible argument to the existing `A.Compose` construction in `PipelineService.build_pipeline`:

```python
return A.Compose(
    transforms,
    bbox_params=bbox_params,
    keypoint_params=keypoint_params,
    additional_targets=pipeline.additional_targets,
    is_check_shapes=pipeline.is_check_shapes,
    strict=pipeline.strict,
    seed=pipeline.seed,
    save_applied_params=True,
)
```

- [ ] **Step 4: Implement trace extraction and manifest capture**

Add `build_variant_trace` to `preview_trace.py`. It validates each AlbumentationsX tuple as `(name, params)`, normalizes
the mapping under the shared node and byte budgets, and returns `PreviewVariantTrace`. Missing `applied_transforms` is
accepted as an empty list for existing test doubles. Import `ArtifactStore` only under `TYPE_CHECKING` so
`preview_trace.py` and `preview.py` do not form a runtime import cycle.

Cap applied transforms at `MAX_APPLIED_TRANSFORMS` and verify the final canonical JSON size. If it exceeds
`MAX_VARIANT_TRACE_JSON_BYTES`, retain ordered transform names but replace parameter mappings with per-transform
structural summaries and SHA-256 digests, setting `parameters_truncated=true`. This bounds additive trace data to
4 MiB for the existing maximum 32 inputs times 16 variants.

In `PreviewService._render_preview_in_run_dir`, create `variant_traces: list[PreviewVariantTrace]`, retain the image
artifact reference, and append one trace immediately after saving each image:

```python
image_artifact = self.artifact_store.artifact_ref(output, kind="image", mime_type="image/png")
artifacts.append(image_artifact)
variant_traces.append(
    build_variant_trace(
        image_index=source_index,
        variant_index=variant_index,
        source_path=source_path,
        artifact_uri=image_artifact.uri,
        effective_seed=_effective_variant_seed(request, variant_index),
        transform_result=result,
    )
)
```

Persist the following additive fields:

```python
"summary": {
    # existing fields remain unchanged
    "variant_trace_count": len(variant_traces),
},
"variant_traces": [trace.model_dump(mode="json") for trace in variant_traces],
```

Implement `_effective_variant_seed` so an explicit request seed yields `request.seed + variant_index`, otherwise it
returns `request.pipeline.seed`.

- [ ] **Step 5: Write failing lookup compatibility tests**

Add tests for a matching trace, a legacy manifest without `variant_traces`, malformed non-list trace data, a malformed
trace entry, negative indexes, and an unknown valid index:

```python
def test_get_preview_variant_trace_returns_legacy_unavailable(tmp_path: Path) -> None:
    store, result = _render_real_preview_fixture(tmp_path)
    manifest_path = store.root / result.run_id / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.pop("variant_traces")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    trace = get_preview_variant_trace(store, result.run_id, image_index=0, variant_index=0)

    assert trace.available is False
    assert trace.trace is None
    assert "legacy" in trace.message.lower()
```

- [ ] **Step 6: Implement manifest-backed lookup**

Add this transport-independent function to `preview_trace.py`:

```python
def get_preview_variant_trace(
    artifact_store: ArtifactStore,
    run_id: str,
    *,
    image_index: int,
    variant_index: int,
) -> PreviewVariantTraceResult:
    if image_index < 0 or variant_index < 0:
        raise ValueError("image_index and variant_index must be non-negative")
    manifest = artifact_store.read_manifest(run_id)
    if "variant_traces" not in manifest:
        return PreviewVariantTraceResult(
            run_id=run_id,
            image_index=image_index,
            variant_index=variant_index,
            available=False,
            message="Variant traces are unavailable for this legacy preview run.",
        )
    raw_traces = manifest["variant_traces"]
    if not isinstance(raw_traces, list):
        raise ValueError("Preview manifest variant_traces must be a list")
    traces = _validate_variant_traces(raw_traces)
    trace = next(
        (item for item in traces if item.image_index == image_index and item.variant_index == variant_index),
        None,
    )
    if trace is None:
        raise ValueError(f"Preview variant trace is unavailable for image {image_index}, variant {variant_index}")
    return PreviewVariantTraceResult(
        run_id=run_id,
        image_index=image_index,
        variant_index=variant_index,
        available=True,
        trace=trace,
        message="Applied transform trace is available.",
    )
```

Translate `pydantic.ValidationError` from `_validate_variant_traces` into a stable `ValueError` without exposing local
manifest paths.

- [ ] **Step 7: Run the rendering and compatibility tests**

Run:

```bash
uv run pytest tests/test_preview_trace.py tests/test_pipeline.py tests/test_artifacts.py \
  tests/test_annotation_preview.py tests/test_preview_contact_sheet.py -q
uv run ruff check src/albumentationsx_mcp/preview.py src/albumentationsx_mcp/preview_trace.py \
  src/albumentationsx_mcp/pipeline.py tests/test_preview_trace.py tests/test_pipeline.py tests/test_artifacts.py
uv run ty check src/albumentationsx_mcp/preview.py src/albumentationsx_mcp/preview_trace.py \
  src/albumentationsx_mcp/pipeline.py tests/test_preview_trace.py
```

Expected: all commands exit `0`.

- [ ] **Step 8: Commit trace capture and lookup**

```bash
git add src/albumentationsx_mcp/pipeline.py src/albumentationsx_mcp/preview.py \
  src/albumentationsx_mcp/preview_trace.py tests/test_preview_trace.py tests/test_pipeline.py \
  tests/test_artifacts.py tests/test_annotation_preview.py
git commit -m "feat: trace applied preview transforms"
```

### Task 3: Guided First Preview Application Service

**Files:**
- Create: `src/albumentationsx_mcp/guided_preview.py`
- Create: `tests/test_guided_preview.py`

- [ ] **Step 1: Write failing success and blocked-gate tests**

Build a real fixture with one PNG, `TransformCatalog`, `PipelineService`, `PathPolicy`, `ArtifactStore`,
`PreviewService`, `PreviewRequestValidator`, and `recommend_recipe`. Test:

```python
def test_guided_preview_renders_one_bounded_contact_sheet(tmp_path: Path) -> None:
    image_path = tmp_path / "input.png"
    Image.new("RGB", (24, 24), (96, 128, 160)).save(image_path)
    service, store = _guided_service(tmp_path)

    result = service.run(GuidedPreviewRequest(dataset_path=image_path, max_images=1))

    assert result.status == "rendered"
    assert result.onboarding.preview_ready is True
    assert result.validation is not None and result.validation.valid is True
    assert result.preview is not None
    assert result.contact_sheet is not None and result.contact_sheet.kind == "contact_sheet"
    assert result.trace_available is True
    assert store.read_manifest(result.preview.run_id)["summary"]["variant_trace_count"] == 1
```

Parameterize blocked paths for missing input, outside allowed root, empty directory, and a validator double returning
`valid=False`. Assert `preview is None`, `contact_sheet is None`, `trace_available is False`, and
`store.list_runs() == []`. Add request-model cases for `max_images=0` and `max_images=9`.

- [ ] **Step 2: Run tests and verify the missing service failure**

Run:

```bash
uv run pytest tests/test_guided_preview.py -q
```

Expected: collection fails because `albumentationsx_mcp.guided_preview` does not exist.

- [ ] **Step 3: Implement request/result contracts and orchestration**

Create these contracts in `guided_preview.py`:

```python
class GuidedPreviewRequest(StrictModel):
    dataset_path: Path
    task: str = "classification"
    intensity: Intensity = "low"
    targets: list[str] | None = None
    max_images: int = Field(default=8, ge=1, le=8)


class GuidedPreviewResult(StrictModel):
    status: Literal["rendered", "blocked"]
    onboarding: DatasetOnboardingReport
    validation: PreviewRequestValidationReport | None = None
    normalized_request: dict[str, Any] | None = None
    preview: PreviewResult | None = None
    contact_sheet: ArtifactRef | None = None
    trace_available: bool = False
    next_actions: list[str] = Field(default_factory=list)
```

`GuidedPreviewService.run` must call `build_dataset_onboarding_report`, stop before rendering when onboarding is not
ready, validate `preview_request_template.request`, stop before rendering when validation is invalid, then render the
normalized `PreviewRequest`. Find exactly one `contact_sheet` artifact and raise `RuntimeError` if a successful preview
does not contain it. The rendered next actions must name `trace_preview_variant`, contact-sheet review, and
`adjust_pipeline`; blocked next actions reuse the existing remediation guidance.

- [ ] **Step 4: Run guided-service tests and boundary checks**

Run:

```bash
uv run pytest tests/test_guided_preview.py tests/test_onboarding.py tests/test_preview_validation.py -q
uv run ruff check src/albumentationsx_mcp/guided_preview.py tests/test_guided_preview.py
uv run ty check src/albumentationsx_mcp/guided_preview.py tests/test_guided_preview.py
```

Expected: all commands exit `0`; no FastMCP import appears in `guided_preview.py`.

- [ ] **Step 5: Commit the guided use case**

```bash
git add src/albumentationsx_mcp/guided_preview.py tests/test_guided_preview.py
git commit -m "feat: add guided first preview service"
```

### Task 4: MCP Tools, Profiles, And Contract Snapshots

**Files:**
- Modify: `src/albumentationsx_mcp/adapters/mcp/dependencies.py`
- Modify: `src/albumentationsx_mcp/adapters/mcp/dataset.py`
- Modify: `src/albumentationsx_mcp/adapters/mcp/preview.py`
- Modify: `src/albumentationsx_mcp/adapters/mcp/registration.py`
- Modify: `src/albumentationsx_mcp/server.py`
- Modify: `tests/test_mcp_adapters.py`
- Modify: `tests/test_mcp_profiles.py`
- Modify: `tests/test_mcp_stdio.py`
- Modify: `tests/test_server.py`
- Modify: `tests/fixtures/snapshots/mcp_contract.json`

- [ ] **Step 1: Write failing profile and adapter tests**

Update expected profile counts to:

```python
_EXPECTED_COUNTS = {
    CapabilityProfile.CORE: (16, 9, 1, 0),
    CapabilityProfile.REVIEW: (43, 19, 2, 5),
    CapabilityProfile.DATASET: (27, 11, 2, 0),
    CapabilityProfile.FULL: (47, 20, 2, 5),
}
```

Assert `run_first_preview` is present only in `dataset` and `full`; assert `trace_preview_variant` is present in
`review`, `dataset`, and `full`; assert both are absent from `core`. Update the combined adapter count from 45 to 47.

Add adapter invocation tests that call the registered handler functions directly. The guided handler must return
`status="rendered"`; the trace handler must return the trace from that run.

- [ ] **Step 2: Run contract tests and verify missing-tool failures**

Run:

```bash
uv run pytest tests/test_mcp_profiles.py tests/test_mcp_adapters.py tests/test_server.py -q
```

Expected: failures identify absent tools and old surface counts.

- [ ] **Step 3: Compose `GuidedPreviewService` once**

Add `guided_preview_service: GuidedPreviewService` to `McpDependencies` and its matching test dependency dataclass. In
`create_mcp_server`, compute the selected public surface once and construct the service with a profile-aware recipe
closure:

```python
public_surface = public_surface_for_profile(settings.capability_profile)
guided_preview_service = GuidedPreviewService(
    path_policy=path_policy,
    pipeline_service=pipeline_service,
    preview_service=preview_service,
    preview_validator=preview_validator,
    recipe_builder=lambda **kwargs: recommend_recipe(
        **kwargs,
        available_tools=set(public_surface.tools),
    ),
)
```

Pass the same `public_surface` to `DiagnosticsService` and the guided service through `McpDependencies`. Do not construct
stores or services inside an MCP handler.

- [ ] **Step 4: Register both thin MCP handlers**

Add `run_first_preview` to the dataset adapter:

```python
@mcp.tool(name="run_first_preview")
def run_first_preview_tool(
    dataset_path: str,
    task: str = "classification",
    intensity: Intensity = "low",
    targets: list[str] | None = None,
    max_images: int = 8,
) -> dict[str, Any]:
    request = GuidedPreviewRequest(
        dataset_path=Path(dataset_path),
        task=task,
        intensity=intensity,
        targets=targets,
        max_images=max_images,
    )
    return guided_preview_service.run(request).model_dump(mode="json", exclude_none=True)
```

Add `trace_preview_variant` to the preview adapter:

```python
@mcp.tool(name="trace_preview_variant")
def trace_preview_variant_tool(run_id: str, image_index: int, variant_index: int) -> dict[str, Any]:
    return get_preview_variant_trace(
        artifact_store,
        run_id,
        image_index=image_index,
        variant_index=variant_index,
    ).model_dump(mode="json", exclude_none=True)
```

Extend adapter `SURFACE` declarations and `PUBLIC_TOOLS` in canonical order. Keep `core` unchanged.

- [ ] **Step 5: Add one stdio end-to-end workflow**

Replace the manual dataset onboarding sequence in the dataset-profile stdio test with:

```python
guided = await session.call_tool(
    "run_first_preview",
    {"dataset_path": str(image_path), "task": "classification", "max_images": 1},
)
assert guided.structuredContent is not None
preview = guided.structuredContent["preview"]
trace = await session.call_tool(
    "trace_preview_variant",
    {"run_id": preview["run_id"], "image_index": 0, "variant_index": 0},
)
contact_sheet = await session.read_resource(AnyUrl(next(
    artifact["uri"] for artifact in preview["artifacts"] if artifact["kind"] == "contact_sheet"
)))
```

Assert no tool errors, `status == "rendered"`, trace availability, non-empty applied transforms, and PNG resource
content. Keep the existing explicit onboarding/validation coverage in their unit tests.

- [ ] **Step 6: Regenerate the public MCP snapshot**

Run:

```bash
uv run python scripts/export_mcp_contract.py --output tests/fixtures/snapshots/mcp_contract.json
uv run pytest tests/test_mcp_contract_snapshot.py tests/test_contract_snapshot_guard.py -q
```

Expected: both snapshot tests pass and the drift classifier reports no stale contract.

- [ ] **Step 7: Run all MCP/profile integration tests**

Run:

```bash
uv run pytest tests/test_mcp_adapters.py tests/test_mcp_profiles.py tests/test_mcp_stdio.py \
  tests/test_server.py tests/test_diagnostics.py tests/test_host_smoke.py -q
uv run ruff check src/albumentationsx_mcp/adapters/mcp src/albumentationsx_mcp/server.py \
  tests/test_mcp_adapters.py tests/test_mcp_profiles.py tests/test_mcp_stdio.py tests/test_server.py
uv run ty check src/albumentationsx_mcp/adapters/mcp src/albumentationsx_mcp/server.py \
  tests/test_mcp_adapters.py tests/test_mcp_profiles.py tests/test_mcp_stdio.py
```

Expected: all commands exit `0`.

- [ ] **Step 8: Commit the MCP surface**

```bash
git add src/albumentationsx_mcp/adapters/mcp src/albumentationsx_mcp/server.py \
  tests/test_mcp_adapters.py tests/test_mcp_profiles.py tests/test_mcp_stdio.py tests/test_server.py \
  tests/fixtures/snapshots/mcp_contract.json
git commit -m "feat: expose guided preview trace tools"
```

### Task 5: User Workflow Documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/USAGE.md`
- Modify: `docs/FIRST_10_MINUTES.md`
- Modify: `examples/first_10_minutes_prompt.md`
- Modify: `scripts/check_first_10_minutes.py`
- Modify: `tests/test_first_10_minutes.py`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Write the failing documentation guard expectations**

Add `run_first_preview` and `trace_preview_variant` to `_GUIDE_REQUIRED_PHRASES` and `_PROMPT_REQUIRED_PHRASES`. Update
the guard tests so a guide or prompt missing either new tool fails with the missing names in its message.

- [ ] **Step 2: Run the guard tests and verify documentation is stale**

Run:

```bash
uv run pytest tests/test_first_10_minutes.py -q
uv run python scripts/check_first_10_minutes.py
```

Expected: failures report missing `run_first_preview` and `trace_preview_variant` anchors.

- [ ] **Step 3: Document the preferred one-call path and explicit fallback**

Update README `First Preview` to prefer:

```text
Run the host smoke check. If preview_ready is true, call run_first_preview for
/absolute/path/to/images with low intensity and at most 8 images. Show me the contact
sheet. When I mention a specific result, call trace_preview_variant before adjusting it.
```

Keep the explicit `plan_dataset_onboarding` -> `validate_preview_request` -> `render_preview_batch` sequence in
`docs/USAGE.md` as the advanced/fallback path. Add dedicated usage sections for both new tools, document zero-based
indexes, legacy `available=false`, large-array summaries, and the fact that traces are evidence rather than semantic
acceptance decisions.

Update `docs/FIRST_10_MINUTES.md` and `examples/first_10_minutes_prompt.md` so the normal path is smoke ->
`run_first_preview` -> contact sheet -> `trace_preview_variant` -> adjust/compare/export. Retain all legacy guard phrases
inside an explicit fallback paragraph.

Add two concise bullets to `CHANGELOG.md` under `Unreleased`: one for the guided use case and one for additive applied
transform traces.

- [ ] **Step 4: Run documentation and contract guards**

Run:

```bash
uv run pytest tests/test_first_10_minutes.py tests/test_project_scaffolding.py -q
uv run python scripts/check_first_10_minutes.py
uv run python scripts/check_contract_snapshots.py
uv run ruff check scripts/check_first_10_minutes.py tests/test_first_10_minutes.py
```

Expected: all commands exit `0`.

- [ ] **Step 5: Commit the documentation**

```bash
git add README.md docs/USAGE.md docs/FIRST_10_MINUTES.md examples/first_10_minutes_prompt.md \
  scripts/check_first_10_minutes.py tests/test_first_10_minutes.py CHANGELOG.md
git commit -m "docs: simplify the first preview workflow"
```

### Task 6: Full Verification And Delivery

**Files:**
- Verify all changed files
- Do not change package version or create a release tag in this task

- [ ] **Step 1: Run formatting and apply only mechanical formatting changes**

Run:

```bash
uv run ruff format .
uv run ruff check . --fix
```

Expected: commands exit `0`; inspect the diff and retain only changes related to this plan.

- [ ] **Step 2: Run the complete local quality gate**

Run:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run python scripts/check_contract_snapshots.py
uv run python scripts/check_first_10_minutes.py
uv run python scripts/run_golden_evals.py
uv build
```

Expected: every command exits `0`; the test count has no failures, contract snapshots are fresh, golden evaluations
pass, and `dist/` contains one wheel and one source distribution for version `1.19.0`.

- [ ] **Step 3: Inspect the built wheel payload and run an isolated CLI smoke**

Run:

```bash
uv run python -m zipfile -l dist/albumentationsx_mcp-1.19.0-py3-none-any.whl
uvx --no-cache --from dist/albumentationsx_mcp-1.19.0-py3-none-any.whl albumentationsx-mcp --help
```

Expected: the wheel contains `guided_preview.py` and `preview_trace.py`; the isolated command exits `0` and lists
`--capability-profile`.

- [ ] **Step 4: Review the complete diff against the approved spec**

Run:

```bash
git diff main...HEAD --stat
git diff main...HEAD --check
git status --short
```

Expected: only the design, plan, implementation, tests, snapshots, and user documentation from this feature are
present; `git diff --check` is empty; generated `dist/` files remain untracked or ignored.

- [ ] **Step 5: Commit any verification-only mechanical fixes**

If formatting changed tracked files, stage only the feature files that `git status --short` reports as modified:

```bash
git add src/albumentationsx_mcp/guided_preview.py src/albumentationsx_mcp/preview_trace.py \
  src/albumentationsx_mcp/pipeline.py src/albumentationsx_mcp/preview.py \
  src/albumentationsx_mcp/adapters/mcp/dependencies.py src/albumentationsx_mcp/adapters/mcp/dataset.py \
  src/albumentationsx_mcp/adapters/mcp/preview.py src/albumentationsx_mcp/adapters/mcp/registration.py \
  src/albumentationsx_mcp/server.py tests/test_preview_trace.py tests/test_guided_preview.py \
  tests/test_pipeline.py tests/test_artifacts.py tests/test_annotation_preview.py tests/test_mcp_adapters.py \
  tests/test_mcp_profiles.py tests/test_mcp_stdio.py tests/test_server.py
git commit -m "style: format guided preview changes"
```

If `git status --short` is clean, do not create an empty commit.

- [ ] **Step 6: Request independent code review, push, and open a pull request**

Push the feature branch and create the PR with the repository's standard CLI flow:

```bash
git push -u origin codex/guided-preview-traceability
gh pr create --base main --head codex/guided-preview-traceability \
  --title "feat: add guided preview traceability" \
  --body-file /tmp/albu-guided-preview-pr.md
```

Write `/tmp/albu-guided-preview-pr.md` with this exact content before the `gh pr create` call:

```text
Summary:
- render a bounded validated first preview with one MCP tool
- record and query applied transform parameters per image variant
- preserve legacy manifests and focused capability profiles

Verification:
- uv run pytest
- uv run ruff check .
- uv run ruff format --check .
- uv run ty check
- uv run python scripts/check_contract_snapshots.py
- uv run python scripts/run_golden_evals.py
- uv build
```

Merge only after required GitHub checks pass. Do not tag or publish from this plan; versioning and the public demo
runtime are separate decisions.
