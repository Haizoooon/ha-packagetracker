import { defineConfig } from "vite";
import { fileURLToPath } from "node:url";

export default defineConfig({
  build: {
    outDir: fileURLToPath(
      new URL("../custom_components/package_tracker/frontend", import.meta.url),
    ),
    emptyOutDir: false,
    target: "es2022",
    minify: "esbuild",
    sourcemap: false,
    lib: {
      entry: fileURLToPath(new URL("src/package-tracker-card.ts", import.meta.url)),
      formats: ["es"],
      fileName: () => "package-tracker-card.js",
    },
    rollupOptions: {
      output: {
        inlineDynamicImports: true,
        assetFileNames: "package-tracker-card.[ext]",
      },
    },
  },
});
