export type FeedbackSeverity = "low" | "medium" | "high";
export type ReviewMode = "image" | "overlay";

export interface PreviewArtifact {
  kind: string;
  uri: string;
  mime_type?: string;
  path?: string;
}

export interface PreviewToolResult {
  run_id: string;
  artifacts: PreviewArtifact[];
}

export interface ReviewItem {
  imageIndex: number;
  variantIndex: number;
  label: string;
  imageUri: string;
  overlayUri?: string;
}

export interface ContactSheetUris {
  imageUri?: string;
  overlayUri?: string;
}

export interface FeedbackTagDefinition {
  name: string;
  description: string;
}

interface MutableReviewItem {
  imageIndex: number;
  variantIndex: number;
  imageUri?: string;
  overlayUri?: string;
}

const INDEXED_ARTIFACT_PATTERN = /\/(\d{3})-(\d{3})(-overlay)?\.png$/;
const FEEDBACK_TAG_PATTERN = /^[a-z][a-z0-9_]*$/;
const RUN_ID_PATTERN = /^[0-9a-f]{32}$/;
const MAX_ARTIFACTS = 1100;
const MAX_FEEDBACK_TAGS = 32;
const MAX_NOTE_LENGTH = 500;

export function parsePreviewToolResult(
  value: unknown,
): PreviewToolResult | undefined {
  if (
    !isRecord(value) ||
    typeof value.run_id !== "string" ||
    !RUN_ID_PATTERN.test(value.run_id)
  ) {
    return undefined;
  }
  if (!Array.isArray(value.artifacts)) {
    return undefined;
  }

  const artifactPrefix = `artifact://${value.run_id}/`;
  const artifacts = value.artifacts
    .slice(0, MAX_ARTIFACTS)
    .flatMap((artifact): PreviewArtifact[] => {
      if (
        !isRecord(artifact) ||
        typeof artifact.kind !== "string" ||
        typeof artifact.uri !== "string" ||
        !artifact.uri.startsWith(artifactPrefix)
      ) {
        return [];
      }
      return [
        {
          kind: artifact.kind,
          uri: artifact.uri,
          ...(typeof artifact.mime_type === "string"
            ? { mime_type: artifact.mime_type }
            : {}),
        },
      ];
    });

  return { run_id: value.run_id, artifacts };
}

export function parseFeedbackTagCatalog(
  value: unknown,
): FeedbackTagDefinition[] {
  if (!isRecord(value) || !Array.isArray(value.tags)) {
    return [];
  }
  return value.tags
    .slice(0, MAX_FEEDBACK_TAGS)
    .flatMap((tag): FeedbackTagDefinition[] => {
      if (
        !isRecord(tag) ||
        typeof tag.name !== "string" ||
        !FEEDBACK_TAG_PATTERN.test(tag.name) ||
        typeof tag.description !== "string" ||
        tag.description.trim().length === 0
      ) {
        return [];
      }
      return [{ name: tag.name, description: tag.description.trim() }];
    });
}

export function buildReviewItems(result: PreviewToolResult): ReviewItem[] {
  const indexed = new Map<string, MutableReviewItem>();

  for (const artifact of result.artifacts) {
    if (
      artifact.mime_type !== "image/png" ||
      (artifact.kind !== "image" && artifact.kind !== "overlay")
    ) {
      continue;
    }
    const match = INDEXED_ARTIFACT_PATTERN.exec(artifact.uri);
    if (!match) {
      continue;
    }
    const imageIndexText = match[1];
    const variantIndexText = match[2];
    if (imageIndexText === undefined || variantIndexText === undefined) {
      continue;
    }
    const hasOverlaySuffix = match[3] !== undefined;
    if ((artifact.kind === "overlay") !== hasOverlaySuffix) {
      continue;
    }

    const imageIndex = Number.parseInt(imageIndexText, 10);
    const variantIndex = Number.parseInt(variantIndexText, 10);
    const key = `${imageIndex}:${variantIndex}`;
    const item = indexed.get(key) ?? { imageIndex, variantIndex };
    if (artifact.kind === "image") {
      item.imageUri = artifact.uri;
    } else {
      item.overlayUri = artifact.uri;
    }
    indexed.set(key, item);
  }

  return [...indexed.values()]
    .filter(
      (item): item is MutableReviewItem & { imageUri: string } =>
        item.imageUri !== undefined,
    )
    .sort(
      (left, right) =>
        left.imageIndex - right.imageIndex ||
        left.variantIndex - right.variantIndex,
    )
    .map((item) => ({
      imageIndex: item.imageIndex,
      variantIndex: item.variantIndex,
      label: `Image ${item.imageIndex + 1} / Variant ${item.variantIndex + 1}`,
      imageUri: item.imageUri,
      ...(item.overlayUri ? { overlayUri: item.overlayUri } : {}),
    }));
}

export function findContactSheetUris(
  result: PreviewToolResult,
): ContactSheetUris {
  const imageUri = result.artifacts.find(
    (artifact) =>
      artifact.kind === "contact_sheet" &&
      artifact.mime_type === "image/png" &&
      artifact.uri.endsWith("/contact_sheet.png"),
  )?.uri;
  const overlayUri = result.artifacts.find(
    (artifact) =>
      artifact.kind === "overlay_contact_sheet" &&
      artifact.mime_type === "image/png" &&
      artifact.uri.endsWith("/overlay_contact_sheet.png"),
  )?.uri;

  return {
    ...(imageUri ? { imageUri } : {}),
    ...(overlayUri ? { overlayUri } : {}),
  };
}

export function moveSelection(
  currentIndex: number,
  delta: number,
  itemCount: number,
): number {
  if (itemCount <= 0) {
    return 0;
  }
  const boundedCurrent = Math.min(Math.max(currentIndex, 0), itemCount - 1);
  return Math.min(Math.max(boundedCurrent + delta, 0), itemCount - 1);
}

export function composeFeedbackTags(
  tags: Iterable<string>,
  severity: FeedbackSeverity,
): string[] {
  const unique = new Set<string>();
  for (const tag of tags) {
    const normalized = tag.trim();
    if (FEEDBACK_TAG_PATTERN.test(normalized)) {
      unique.add(normalized);
    }
  }
  return [...unique].sort().map((tag) => `${tag}:${severity}`);
}

export function publicRunLabel(runId: string): string {
  const shortId = /^[0-9a-f]{8,}$/i.test(runId) ? runId.slice(0, 8) : "pending";
  return `Run ${shortId}`;
}

export function sanitizeNote(note: string): string {
  return note.trim().slice(0, MAX_NOTE_LENGTH);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
