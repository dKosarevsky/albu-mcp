import { describe, expect, it } from "vitest";

import {
  buildReviewItems,
  composeFeedbackTags,
  findContactSheetUris,
  moveSelection,
  parseFeedbackTagCatalog,
  parsePreviewToolResult,
  publicRunLabel,
  sanitizeNote,
  type PreviewToolResult,
} from "./review-state";

const result: PreviewToolResult = {
  run_id: "0123456789abcdef0123456789abcdef",
  artifacts: [
    {
      kind: "image",
      uri: "artifact://0123456789abcdef0123456789abcdef/000-000.png",
      path: "/Users/reviewer/private-dataset/cat.png",
      mime_type: "image/png",
    },
    {
      kind: "overlay",
      uri: "artifact://0123456789abcdef0123456789abcdef/000-000-overlay.png",
      path: "/Users/reviewer/private-dataset/cat-overlay.png",
      mime_type: "image/png",
    },
    {
      kind: "image",
      uri: "artifact://0123456789abcdef0123456789abcdef/000-001.png",
      path: "/Users/reviewer/private-dataset/cat-second.png",
      mime_type: "image/png",
    },
    {
      kind: "contact_sheet",
      uri: "artifact://0123456789abcdef0123456789abcdef/contact_sheet.png",
      path: "/Users/reviewer/private-dataset/contact_sheet.png",
      mime_type: "image/png",
    },
    {
      kind: "overlay_contact_sheet",
      uri: "artifact://0123456789abcdef0123456789abcdef/overlay_contact_sheet.png",
      path: "/Users/reviewer/private-dataset/overlay_contact_sheet.png",
      mime_type: "image/png",
    },
  ],
};

describe("buildReviewItems", () => {
  it("maps image and overlay artifacts to ordinal review items", () => {
    expect(buildReviewItems(result)).toEqual([
      {
        imageIndex: 0,
        variantIndex: 0,
        label: "Image 1 / Variant 1",
        imageUri: "artifact://0123456789abcdef0123456789abcdef/000-000.png",
        overlayUri:
          "artifact://0123456789abcdef0123456789abcdef/000-000-overlay.png",
      },
      {
        imageIndex: 0,
        variantIndex: 1,
        label: "Image 1 / Variant 2",
        imageUri: "artifact://0123456789abcdef0123456789abcdef/000-001.png",
      },
    ]);
  });

  it("does not copy private artifact paths into view state", () => {
    expect(JSON.stringify(buildReviewItems(result))).not.toContain(
      "private-dataset",
    );
  });

  it("ignores malformed and non-PNG image artifacts", () => {
    const malformed: PreviewToolResult = {
      run_id: result.run_id,
      artifacts: [
        {
          kind: "image",
          uri: "artifact://run/not-indexed.png",
          mime_type: "image/png",
        },
        {
          kind: "image",
          uri: `${result.artifacts[0]?.uri}.json`,
          mime_type: "application/json",
        },
      ],
    };

    expect(buildReviewItems(malformed)).toEqual([]);
  });
});

it("finds standard and overlay contact sheets without exposing paths", () => {
  expect(findContactSheetUris(result)).toEqual({
    imageUri: "artifact://0123456789abcdef0123456789abcdef/contact_sheet.png",
    overlayUri:
      "artifact://0123456789abcdef0123456789abcdef/overlay_contact_sheet.png",
  });
});

it("keeps selection inside the available item range", () => {
  expect(moveSelection(0, -1, 2)).toBe(0);
  expect(moveSelection(0, 1, 2)).toBe(1);
  expect(moveSelection(1, 1, 2)).toBe(1);
  expect(moveSelection(4, 1, 0)).toBe(0);
});

it("composes canonical severity-aware feedback tags", () => {
  expect(
    composeFeedbackTags(
      ["too_noisy", "object_unrecognizable", "too_noisy"],
      "high",
    ),
  ).toEqual(["object_unrecognizable:high", "too_noisy:high"]);
});

it("uses a short public run label and clamps notes to the server limit", () => {
  expect(publicRunLabel(result.run_id)).toBe("Run 01234567");
  expect(sanitizeNote(`  ${"x".repeat(510)}  `)).toHaveLength(500);
  expect(sanitizeNote("  inspect the boundary  ")).toBe("inspect the boundary");
});

it("parses tool output into a path-free preview contract", () => {
  expect(
    parsePreviewToolResult({
      run_id: result.run_id,
      artifacts: result.artifacts,
      pipeline: { transforms: [] },
    }),
  ).toEqual({
    run_id: result.run_id,
    artifacts: result.artifacts.map(({ kind, uri, mime_type }) => ({
      kind,
      uri,
      mime_type,
    })),
  });
  expect(JSON.stringify(parsePreviewToolResult(result))).not.toContain(
    "private-dataset",
  );
  expect(
    parsePreviewToolResult({ run_id: "not-a-run", artifacts: [] }),
  ).toBeUndefined();
});

it("parses a bounded feedback tag catalog and rejects malformed entries", () => {
  expect(
    parseFeedbackTagCatalog({
      tags: [
        { name: "too_noisy", description: "Noise hides details." },
        { name: "INVALID", description: "ignored" },
        { name: "too_blurry", description: 4 },
      ],
    }),
  ).toEqual([{ name: "too_noisy", description: "Noise hides details." }]);
  expect(parseFeedbackTagCatalog({ tags: "not-an-array" })).toEqual([]);
});
