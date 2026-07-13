import { fileURLToPath } from "node:url";

import { defineConfig, type Plugin } from "vite";
import { viteSingleFile } from "vite-plugin-singlefile";

const root = fileURLToPath(new URL(".", import.meta.url));
const output = fileURLToPath(
  new URL("../src/albumentationsx_mcp/ui", import.meta.url),
);

function normalizeOutputWhitespace(): Plugin {
  return {
    name: "normalize-output-whitespace",
    enforce: "post",
    generateBundle(_options, bundle) {
      for (const entry of Object.values(bundle)) {
        if (
          entry.type === "asset" &&
          entry.fileName.endsWith(".html") &&
          typeof entry.source === "string"
        ) {
          entry.source = entry.source.replace(/[ \t]+$/gm, "");
        }
      }
    },
  };
}

export default defineConfig({
  root,
  plugins: [viteSingleFile(), normalizeOutputWhitespace()],
  build: {
    outDir: output,
    emptyOutDir: false,
    rollupOptions: {
      input: fileURLToPath(new URL("preview-review.html", import.meta.url)),
    },
  },
});
