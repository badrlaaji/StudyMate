// Unit tests of the front end (Node, no browser): `npm test`.
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: { alias: [{ find: /^@\//, replacement: fileURLToPath(new URL("./", import.meta.url)) }] },
  test: { include: ["tests/**/*.test.ts"], environment: "node" },
});
