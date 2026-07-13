import {
  App,
  applyDocumentTheme,
  applyHostFonts,
  applyHostStyleVariables,
  type McpUiHostContext,
} from "@modelcontextprotocol/ext-apps";
import {
  AlertTriangle,
  Check,
  ChevronLeft,
  ChevronRight,
  Image as ImageIcon,
  Layers3,
  LoaderCircle,
  Maximize2,
  Minimize2,
  Save,
  createIcons,
} from "lucide";

import {
  buildReviewItems,
  composeFeedbackTags,
  findContactSheetUris,
  moveSelection,
  parseFeedbackTagCatalog,
  parsePreviewToolResult,
  publicRunLabel,
  sanitizeNote,
  type ContactSheetUris,
  type FeedbackSeverity,
  type FeedbackTagDefinition,
  type PreviewToolResult,
  type ReviewItem,
  type ReviewMode,
} from "./review-state";
import "./styles.css";

const FALLBACK_FEEDBACK_TAGS: FeedbackTagDefinition[] = [
  { name: "too_noisy", description: "Noise hides task-relevant detail." },
  {
    name: "too_blurry",
    description: "Blur removes detail needed for the task.",
  },
  { name: "too_distorted", description: "Geometry is no longer realistic." },
  { name: "too_dark", description: "Task evidence is underexposed." },
  { name: "too_bright", description: "Task evidence is overexposed." },
  {
    name: "exposure_too_weak",
    description: "Exposure variation is too subtle.",
  },
  { name: "color_shift", description: "Color variation looks unrealistic." },
  {
    name: "object_unrecognizable",
    description: "The labeled object or class evidence is lost.",
  },
];

const ICONS = {
  AlertTriangle,
  Check,
  ChevronLeft,
  ChevronRight,
  Image: ImageIcon,
  Layers3,
  LoaderCircle,
  Maximize2,
  Minimize2,
  Save,
};

interface ReviewDraft {
  tags: Set<string>;
  severity: FeedbackSeverity;
  note: string;
}

type FeedbackStatus = "accepted" | "recorded";

const app = new App(
  { name: "albumentationsx-preview-review", version: "1.18.0" },
  {},
  { autoResize: true, strict: true },
);

const root = requireElement<HTMLElement>("#app");
root.innerHTML = `
  <div class="app-shell">
    <header class="app-bar">
      <div class="app-title">
        <span class="brand-mark" aria-hidden="true"></span>
        <div>
          <h1>Preview review</h1>
          <p id="run-summary">Waiting for preview</p>
        </div>
      </div>
      <button id="display-mode" class="icon-button" type="button" title="Enter fullscreen" aria-label="Enter fullscreen" hidden>
        <i data-lucide="maximize-2"></i>
      </button>
    </header>

    <section id="app-state" class="app-state" role="status">
      <span id="state-icon" class="state-icon"><i data-lucide="loader-circle"></i></span>
      <h2 id="state-title">Connecting</h2>
      <p id="state-message">Waiting for the host.</p>
    </section>

    <div id="workspace" class="workspace" hidden>
      <section class="viewer" aria-labelledby="selected-label">
        <div class="viewer-heading">
          <div>
            <p class="section-label">Selected output</p>
            <h2 id="selected-label">Image 1 / Variant 1</h2>
          </div>
          <div class="segmented-control" role="group" aria-label="Preview layer">
            <button class="segment is-active" type="button" data-mode="image" aria-pressed="true">
              <i data-lucide="image"></i><span>Image</span>
            </button>
            <button class="segment" type="button" data-mode="overlay" aria-pressed="false">
              <i data-lucide="layers-3"></i><span>Overlay</span>
            </button>
          </div>
        </div>

        <div class="preview-viewport">
          <img id="preview-image" alt="Selected augmented preview" hidden />
          <div id="media-state" class="media-state" role="status">
            <i data-lucide="loader-circle"></i><span>Loading preview</span>
          </div>
        </div>

        <div class="preview-navigation">
          <button id="previous-item" class="icon-button" type="button" title="Previous variant" aria-label="Previous variant">
            <i data-lucide="chevron-left"></i>
          </button>
          <div class="selection-fields">
            <label>Image<select id="image-select" aria-label="Image"></select></label>
            <label>Variant<select id="variant-select" aria-label="Variant"></select></label>
          </div>
          <button id="next-item" class="icon-button" type="button" title="Next variant" aria-label="Next variant">
            <i data-lucide="chevron-right"></i>
          </button>
        </div>

        <figure id="contact-sheet-wrap" class="contact-sheet" hidden>
          <img id="contact-sheet" alt="Batch contact sheet" />
          <figcaption>Batch overview</figcaption>
        </figure>
      </section>

      <aside class="feedback" aria-labelledby="feedback-heading">
        <div class="feedback-heading">
          <div>
            <p class="section-label">Decision</p>
            <h2 id="feedback-heading">Review variant</h2>
          </div>
          <span id="decision-badge" class="decision-badge" hidden></span>
        </div>

        <fieldset class="issue-fieldset">
          <legend>Issues</legend>
          <div id="issue-options" class="issue-options"></div>
        </fieldset>

        <fieldset class="severity-fieldset">
          <legend>Severity</legend>
          <div class="segmented-control severity-control">
            <label class="segment"><input type="radio" name="severity" value="low" /><span>Low</span></label>
            <label class="segment is-active"><input type="radio" name="severity" value="medium" checked /><span>Medium</span></label>
            <label class="segment"><input type="radio" name="severity" value="high" /><span>High</span></label>
          </div>
        </fieldset>

        <label class="note-field" for="feedback-note">
          <span>Note <small>optional</small></span>
          <textarea id="feedback-note" maxlength="500" rows="3" placeholder="Task-specific observation"></textarea>
          <span id="note-count" class="note-count">0 / 500</span>
        </label>

        <p id="feedback-status" class="feedback-status" role="status"></p>
        <div class="feedback-actions">
          <button id="record-feedback" class="button secondary" type="button" disabled>
            <i data-lucide="save"></i><span>Record issue</span>
          </button>
          <button id="accept-variant" class="button primary" type="button">
            <i data-lucide="check"></i><span>Accept variant</span>
          </button>
        </div>
      </aside>
    </div>
  </div>
`;

const statePanel = requireElement<HTMLElement>("#app-state");
const stateIcon = requireElement<HTMLElement>("#state-icon");
const stateTitle = requireElement<HTMLElement>("#state-title");
const stateMessage = requireElement<HTMLElement>("#state-message");
const workspace = requireElement<HTMLElement>("#workspace");
const runSummary = requireElement<HTMLElement>("#run-summary");
const selectedLabel = requireElement<HTMLElement>("#selected-label");
const previewImage = requireElement<HTMLImageElement>("#preview-image");
const mediaState = requireElement<HTMLElement>("#media-state");
const contactSheetWrap = requireElement<HTMLElement>("#contact-sheet-wrap");
const contactSheet = requireElement<HTMLImageElement>("#contact-sheet");
const imageSelect = requireElement<HTMLSelectElement>("#image-select");
const variantSelect = requireElement<HTMLSelectElement>("#variant-select");
const previousButton = requireElement<HTMLButtonElement>("#previous-item");
const nextButton = requireElement<HTMLButtonElement>("#next-item");
const displayModeButton = requireElement<HTMLButtonElement>("#display-mode");
const issueOptions = requireElement<HTMLElement>("#issue-options");
const feedbackNote = requireElement<HTMLTextAreaElement>("#feedback-note");
const noteCount = requireElement<HTMLElement>("#note-count");
const feedbackStatus = requireElement<HTMLElement>("#feedback-status");
const recordFeedbackButton =
  requireElement<HTMLButtonElement>("#record-feedback");
const acceptVariantButton =
  requireElement<HTMLButtonElement>("#accept-variant");
const decisionBadge = requireElement<HTMLElement>("#decision-badge");
const modeButtons = [
  ...root.querySelectorAll<HTMLButtonElement>("[data-mode]"),
];
const severityInputs = [
  ...root.querySelectorAll<HTMLInputElement>('input[name="severity"]'),
];

let connected = false;
let previewResult: PreviewToolResult | undefined;
let reviewItems: ReviewItem[] = [];
let contactSheetUris: ContactSheetUris = {};
let feedbackTagCatalog = FALLBACK_FEEDBACK_TAGS;
let selectedIndex = 0;
let reviewMode: ReviewMode = "image";
let displayMode: "inline" | "fullscreen" | "pip" = "inline";
let saving = false;
let mediaEpoch = 0;
let resourceGeneration = 0;
const resourceUrls = new Map<string, string>();
const resourceLoads = new Map<string, Promise<string>>();
const drafts = new Map<string, ReviewDraft>();
const feedbackByItem = new Map<string, FeedbackStatus>();

renderIcons(root);
renderFeedbackTagOptions();

app.ontoolinput = () => {
  showAppState(
    "loading",
    "Rendering preview",
    "Waiting for preview artifacts.",
  );
};

app.ontoolresult = (params) => {
  if (params.isError) {
    showAppState(
      "error",
      "Preview unavailable",
      "The preview tool did not complete successfully.",
    );
    return;
  }
  const parsed = parsePreviewToolResult(params.structuredContent);
  if (!parsed) {
    showAppState(
      "error",
      "Preview unavailable",
      "The preview result did not match the expected contract.",
    );
    return;
  }
  acceptPreviewResult(parsed);
};

app.ontoolcancelled = () => {
  showAppState(
    "error",
    "Preview cancelled",
    "No review artifacts were produced.",
  );
};

app.onhostcontextchanged = () => {
  applyHostContext(app.getHostContext());
};

app.onteardown = () => {
  releaseResourceUrls();
  return {};
};

app.onerror = () => {
  showAppState(
    "error",
    "Connection interrupted",
    "The host connection is not available.",
  );
};

previousButton.addEventListener("click", () =>
  selectItem(moveSelection(selectedIndex, -1, reviewItems.length)),
);
nextButton.addEventListener("click", () =>
  selectItem(moveSelection(selectedIndex, 1, reviewItems.length)),
);

imageSelect.addEventListener("change", () => {
  const imageIndex = Number.parseInt(imageSelect.value, 10);
  const nextIndex = reviewItems.findIndex(
    (item) => item.imageIndex === imageIndex,
  );
  if (nextIndex >= 0) {
    selectItem(nextIndex);
  }
});

variantSelect.addEventListener("change", () => {
  const current = getSelectedItem();
  if (!current) {
    return;
  }
  const variantIndex = Number.parseInt(variantSelect.value, 10);
  const nextIndex = reviewItems.findIndex(
    (item) =>
      item.imageIndex === current.imageIndex &&
      item.variantIndex === variantIndex,
  );
  if (nextIndex >= 0) {
    selectItem(nextIndex);
  }
});

for (const button of modeButtons) {
  button.addEventListener("click", () => {
    const mode = button.dataset.mode;
    if (mode !== "image" && mode !== "overlay") {
      return;
    }
    const item = getSelectedItem();
    if (mode === "overlay" && !item?.overlayUri) {
      return;
    }
    reviewMode = mode;
    renderSelection();
    void refreshMedia();
  });
}

for (const input of severityInputs) {
  input.addEventListener("change", () => {
    if (
      !input.checked ||
      (input.value !== "low" &&
        input.value !== "medium" &&
        input.value !== "high")
    ) {
      return;
    }
    getCurrentDraft().severity = input.value;
    renderSeverity();
    updateActionState();
  });
}

feedbackNote.addEventListener("input", () => {
  getCurrentDraft().note = feedbackNote.value;
  noteCount.textContent = `${feedbackNote.value.length} / 500`;
  updateActionState();
});

recordFeedbackButton.addEventListener("click", () => void saveFeedback(false));
acceptVariantButton.addEventListener("click", () => void saveFeedback(true));
displayModeButton.addEventListener("click", () => void toggleDisplayMode());

document.addEventListener("keydown", (event) => {
  if (event.defaultPrevented || isFormControl(event.target)) {
    return;
  }
  if (event.key === "ArrowLeft") {
    event.preventDefault();
    selectItem(moveSelection(selectedIndex, -1, reviewItems.length));
  } else if (event.key === "ArrowRight") {
    event.preventDefault();
    selectItem(moveSelection(selectedIndex, 1, reviewItems.length));
  }
});

void connect();

async function connect(): Promise<void> {
  try {
    await app.connect();
    connected = true;
    applyHostContext(app.getHostContext());
    if (previewResult) {
      showWorkspace();
      renderSelection();
      void refreshMedia();
    } else {
      showAppState(
        "waiting",
        "Waiting for preview",
        "No preview result has been received yet.",
      );
    }
    void loadFeedbackTagCatalog();
  } catch {
    showAppState(
      "error",
      "Host unavailable",
      "The MCP App could not connect to the host.",
    );
  }
}

function acceptPreviewResult(result: PreviewToolResult): void {
  releaseResourceUrls();
  previewResult = result;
  reviewItems = buildReviewItems(result);
  contactSheetUris = findContactSheetUris(result);
  selectedIndex = 0;
  reviewMode = "image";
  drafts.clear();
  feedbackByItem.clear();

  if (reviewItems.length === 0) {
    showAppState(
      "error",
      "No review images",
      "The preview result did not contain readable PNG variants.",
    );
    return;
  }
  renderSelectors();
  renderSelection();
  showWorkspace();
  if (connected) {
    void refreshMedia();
  }
}

function showWorkspace(): void {
  statePanel.hidden = true;
  workspace.hidden = false;
}

function showAppState(
  kind: "loading" | "waiting" | "error",
  title: string,
  message: string,
): void {
  workspace.hidden = true;
  statePanel.hidden = false;
  statePanel.dataset.kind = kind;
  stateTitle.textContent = title;
  stateMessage.textContent = message;
  replaceIcon(stateIcon, kind === "error" ? "alert-triangle" : "loader-circle");
  stateIcon.classList.toggle("is-spinning", kind === "loading");
}

function selectItem(index: number): void {
  const nextIndex = moveSelection(index, 0, reviewItems.length);
  if (nextIndex === selectedIndex && getSelectedItem()) {
    return;
  }
  selectedIndex = nextIndex;
  const item = getSelectedItem();
  if (reviewMode === "overlay" && !item?.overlayUri) {
    reviewMode = "image";
  }
  renderSelectors();
  renderSelection();
  void refreshMedia();
}

function renderSelection(): void {
  const item = getSelectedItem();
  if (!item || !previewResult) {
    return;
  }
  const draft = getCurrentDraft();
  runSummary.textContent = `${publicRunLabel(previewResult.run_id)} · ${selectedIndex + 1} of ${reviewItems.length}`;
  selectedLabel.textContent = item.label;
  feedbackNote.value = draft.note;
  noteCount.textContent = `${draft.note.length} / 500`;

  for (const button of modeButtons) {
    const mode = button.dataset.mode;
    const active = mode === reviewMode;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
    button.disabled = mode === "overlay" && !item.overlayUri;
  }
  renderFeedbackTagOptions();
  renderSeverity();
  renderDecisionBadge();
  updateActionState();
}

function renderSelectors(): void {
  const item = getSelectedItem();
  if (!item) {
    return;
  }
  const imageIndices = [
    ...new Set(reviewItems.map((candidate) => candidate.imageIndex)),
  ];
  replaceSelectOptions(
    imageSelect,
    imageIndices.map((imageIndex) => ({
      value: String(imageIndex),
      label: String(imageIndex + 1),
    })),
    String(item.imageIndex),
  );
  replaceSelectOptions(
    variantSelect,
    reviewItems
      .filter((candidate) => candidate.imageIndex === item.imageIndex)
      .map((candidate) => ({
        value: String(candidate.variantIndex),
        label: String(candidate.variantIndex + 1),
      })),
    String(item.variantIndex),
  );
}

function renderFeedbackTagOptions(): void {
  const draft = getCurrentDraft();
  issueOptions.replaceChildren();
  for (const tag of feedbackTagCatalog) {
    const label = document.createElement("label");
    label.className = "issue-option";
    label.title = tag.description;
    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = tag.name;
    input.checked = draft.tags.has(tag.name);
    input.addEventListener("change", () => {
      if (input.checked) {
        draft.tags.add(tag.name);
      } else {
        draft.tags.delete(tag.name);
      }
      updateActionState();
    });
    const text = document.createElement("span");
    text.textContent = humanizeTag(tag.name);
    label.append(input, text);
    issueOptions.append(label);
  }
}

function renderSeverity(): void {
  const severity = getCurrentDraft().severity;
  for (const input of severityInputs) {
    const active = input.value === severity;
    input.checked = active;
    input.closest("label")?.classList.toggle("is-active", active);
  }
}

function renderDecisionBadge(): void {
  const status = feedbackByItem.get(getCurrentItemKey());
  decisionBadge.hidden = status === undefined;
  decisionBadge.textContent =
    status === "accepted"
      ? "Accepted"
      : status === "recorded"
        ? "Issue recorded"
        : "";
  decisionBadge.dataset.status = status ?? "";
}

function updateActionState(): void {
  const hasItem = getSelectedItem() !== undefined;
  const draft = getCurrentDraft();
  recordFeedbackButton.disabled =
    !connected ||
    !hasItem ||
    saving ||
    (draft.tags.size === 0 && sanitizeNote(draft.note).length === 0);
  acceptVariantButton.disabled = !connected || !hasItem || saving;
  previousButton.disabled = selectedIndex <= 0 || saving;
  nextButton.disabled = selectedIndex >= reviewItems.length - 1 || saving;
  imageSelect.disabled = saving;
  variantSelect.disabled = saving;
}

async function refreshMedia(): Promise<void> {
  if (!connected) {
    return;
  }
  const item = getSelectedItem();
  if (!item) {
    return;
  }
  const epoch = ++mediaEpoch;
  const selectedUri =
    reviewMode === "overlay" ? item.overlayUri : item.imageUri;
  const sheetUri =
    reviewMode === "overlay"
      ? contactSheetUris.overlayUri
      : contactSheetUris.imageUri;
  if (!selectedUri) {
    return;
  }

  previewImage.hidden = true;
  previewImage.removeAttribute("src");
  setMediaState("loading", "Loading preview");
  contactSheetWrap.hidden = true;
  contactSheet.removeAttribute("src");

  try {
    const [selectedUrl, sheetUrl] = await Promise.all([
      loadResourceUrl(selectedUri),
      sheetUri ? loadResourceUrl(sheetUri) : Promise.resolve(undefined),
    ]);
    if (epoch !== mediaEpoch) {
      return;
    }
    previewImage.src = selectedUrl;
    previewImage.alt = `${item.label}${reviewMode === "overlay" ? " annotation overlay" : " augmented preview"}`;
    previewImage.hidden = false;
    mediaState.hidden = true;
    if (sheetUrl) {
      contactSheet.src = sheetUrl;
      contactSheet.alt =
        reviewMode === "overlay"
          ? "Batch overlay contact sheet"
          : "Batch image contact sheet";
      contactSheetWrap.hidden = false;
    }
  } catch {
    if (epoch === mediaEpoch) {
      setMediaState("error", "Preview image unavailable");
    }
  }
}

async function loadResourceUrl(uri: string): Promise<string> {
  const cached = resourceUrls.get(uri);
  if (cached) {
    return cached;
  }
  const pending = resourceLoads.get(uri);
  if (pending) {
    return pending;
  }
  const generation = resourceGeneration;
  const load = (async () => {
    const result = await app.readServerResource({ uri });
    const content = result.contents.find(
      (candidate): candidate is typeof candidate & { blob: string } =>
        "blob" in candidate && typeof candidate.blob === "string",
    );
    if (!content) {
      throw new Error("Binary resource content is missing");
    }
    if (content.mimeType !== undefined && content.mimeType !== "image/png") {
      throw new Error("Unexpected preview resource type");
    }
    const binary = atob(content.blob);
    const bytes = Uint8Array.from(binary, (character) =>
      character.charCodeAt(0),
    );
    const objectUrl = URL.createObjectURL(
      new Blob([bytes], { type: content.mimeType ?? "image/png" }),
    );
    if (generation !== resourceGeneration) {
      URL.revokeObjectURL(objectUrl);
      throw new Error("Preview resource was superseded");
    }
    resourceUrls.set(uri, objectUrl);
    return objectUrl;
  })();
  resourceLoads.set(uri, load);
  try {
    return await load;
  } finally {
    resourceLoads.delete(uri);
  }
}

function releaseResourceUrls(): void {
  mediaEpoch += 1;
  resourceGeneration += 1;
  for (const url of resourceUrls.values()) {
    URL.revokeObjectURL(url);
  }
  resourceUrls.clear();
  resourceLoads.clear();
}

function setMediaState(kind: "loading" | "error", message: string): void {
  mediaState.hidden = false;
  mediaState.dataset.kind = kind;
  replaceIcon(
    mediaState,
    kind === "error" ? "alert-triangle" : "loader-circle",
    message,
  );
  mediaState.classList.toggle("is-spinning", kind === "loading");
}

async function loadFeedbackTagCatalog(): Promise<void> {
  try {
    const result = await app.callServerTool({
      name: "list_feedback_tags",
      arguments: {},
    });
    if (result.isError) {
      return;
    }
    const catalog = parseFeedbackTagCatalog(result.structuredContent);
    if (catalog.length > 0) {
      feedbackTagCatalog = catalog;
      renderFeedbackTagOptions();
    }
  } catch {
    feedbackTagCatalog = FALLBACK_FEEDBACK_TAGS;
  }
}

async function saveFeedback(accepted: boolean): Promise<void> {
  const item = getSelectedItem();
  if (!item || !previewResult || saving) {
    return;
  }
  const draft = getCurrentDraft();
  saving = true;
  feedbackStatus.textContent = "Saving decision";
  feedbackStatus.dataset.kind = "loading";
  updateActionState();

  try {
    const result = await app.callServerTool({
      name: "record_preview_feedback",
      arguments: {
        run_id: previewResult.run_id,
        image_index: item.imageIndex,
        variant_index: item.variantIndex,
        feedback_tags: composeFeedbackTags(draft.tags, draft.severity),
        note: sanitizeNote(draft.note),
        accepted,
      },
    });
    if (result.isError) {
      throw new Error("Feedback call failed");
    }
    feedbackByItem.set(getCurrentItemKey(), accepted ? "accepted" : "recorded");
    feedbackStatus.textContent = accepted
      ? "Variant accepted"
      : "Issue recorded";
    feedbackStatus.dataset.kind = "success";
    renderDecisionBadge();
  } catch {
    feedbackStatus.textContent = "Decision could not be saved";
    feedbackStatus.dataset.kind = "error";
  } finally {
    saving = false;
    updateActionState();
  }
}

async function toggleDisplayMode(): Promise<void> {
  const context = app.getHostContext();
  const target = displayMode === "fullscreen" ? "inline" : "fullscreen";
  if (!context?.availableDisplayModes?.includes(target)) {
    return;
  }
  try {
    const result = await app.requestDisplayMode({ mode: target });
    displayMode = result.mode;
    renderDisplayModeButton();
  } catch {
    feedbackStatus.textContent = "Display mode is unavailable";
    feedbackStatus.dataset.kind = "error";
  }
}

function applyHostContext(context: McpUiHostContext | undefined): void {
  if (!context) {
    return;
  }
  if (context.theme) {
    applyDocumentTheme(context.theme);
  }
  if (context.styles?.variables) {
    applyHostStyleVariables(context.styles.variables);
  }
  if (context.styles?.css?.fonts) {
    applyHostFonts(context.styles.css.fonts);
  }
  if (context.safeAreaInsets) {
    const rootStyle = document.documentElement.style;
    rootStyle.setProperty("--host-safe-top", `${context.safeAreaInsets.top}px`);
    rootStyle.setProperty(
      "--host-safe-right",
      `${context.safeAreaInsets.right}px`,
    );
    rootStyle.setProperty(
      "--host-safe-bottom",
      `${context.safeAreaInsets.bottom}px`,
    );
    rootStyle.setProperty(
      "--host-safe-left",
      `${context.safeAreaInsets.left}px`,
    );
  }
  displayMode = context.displayMode ?? displayMode;
  document.documentElement.dataset.displayMode = displayMode;
  displayModeButton.hidden =
    !context.availableDisplayModes?.includes("fullscreen");
  renderDisplayModeButton();
}

function renderDisplayModeButton(): void {
  const fullscreen = displayMode === "fullscreen";
  replaceIcon(displayModeButton, fullscreen ? "minimize-2" : "maximize-2");
  const label = fullscreen ? "Exit fullscreen" : "Enter fullscreen";
  displayModeButton.title = label;
  displayModeButton.setAttribute("aria-label", label);
}

function getSelectedItem(): ReviewItem | undefined {
  return reviewItems[selectedIndex];
}

function getCurrentItemKey(): string {
  const item = getSelectedItem();
  return item ? `${item.imageIndex}:${item.variantIndex}` : "none";
}

function getCurrentDraft(): ReviewDraft {
  const key = getCurrentItemKey();
  let draft = drafts.get(key);
  if (!draft) {
    draft = { tags: new Set<string>(), severity: "medium", note: "" };
    drafts.set(key, draft);
  }
  return draft;
}

function replaceSelectOptions(
  select: HTMLSelectElement,
  options: Array<{ value: string; label: string }>,
  selectedValue: string,
): void {
  select.replaceChildren();
  for (const definition of options) {
    const option = document.createElement("option");
    option.value = definition.value;
    option.textContent = definition.label;
    select.append(option);
  }
  select.value = selectedValue;
}

function replaceIcon(
  container: HTMLElement,
  name: string,
  text?: string,
): void {
  container.replaceChildren();
  const icon = document.createElement("i");
  icon.dataset.lucide = name;
  container.append(icon);
  if (text) {
    const label = document.createElement("span");
    label.textContent = text;
    container.append(label);
  }
  renderIcons(container);
}

function renderIcons(container: Element | DocumentFragment): void {
  createIcons({
    icons: ICONS,
    root: container,
    attrs: {
      "aria-hidden": "true",
      width: "18",
      height: "18",
      "stroke-width": "1.8",
    },
  });
}

function humanizeTag(tag: string): string {
  const words = tag.replaceAll("_", " ");
  return `${words.charAt(0).toUpperCase()}${words.slice(1)}`;
}

function isFormControl(target: EventTarget | null): boolean {
  return (
    target instanceof HTMLInputElement ||
    target instanceof HTMLTextAreaElement ||
    target instanceof HTMLSelectElement
  );
}

function requireElement<T extends Element>(selector: string): T {
  const element = document.querySelector<T>(selector);
  if (!element) {
    throw new Error(`Missing required element: ${selector}`);
  }
  return element;
}
