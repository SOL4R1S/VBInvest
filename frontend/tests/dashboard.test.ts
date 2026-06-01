import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";

describe("frontend scaffold", () => {
  it("includes the expected app and test entrypoints", () => {
    const root = join(process.cwd(), "..", "frontend");
    const packageJson = readFileSync(join(root, "package.json"), "utf8");

    expect(packageJson).toContain('"dev": "next dev -p 3000"');
    expect(readFileSync(join(root, "app", "page.tsx"), "utf8")).toContain("data-testid=\"create-watchlist\"");
    expect(readFileSync(join(root, "app", "layout.tsx"), "utf8")).toContain("lang=\"ko\"");
  });
});
