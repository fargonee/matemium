import path from "node:path";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

import { articleContentPlugin } from "./article-content-plugin";

export default defineConfig({
  base: process.env.VITE_BASE || "/",
  plugins: [
    articleContentPlugin(path.resolve(__dirname, "./content/articles")),
    react(),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
  },
  preview: {
    port: 4173,
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
});
