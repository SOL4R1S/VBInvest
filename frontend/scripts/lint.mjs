import { readFileSync } from "node:fs";
import { globSync } from "node:fs";
import { join } from "node:path";

const root = process.cwd();
const files = globSync("**/*.{ts,tsx}", {
  cwd: root,
  exclude: ["node_modules/**", ".next/**"],
});

const banned = [
  { label: "as any", pattern: /\bas\s+any\b/ },
  { label: "@ts-ignore", pattern: /@ts-ignore/ },
  { label: "@ts-expect-error", pattern: /@ts-expect-error/ },
  { label: "200-day MA default", pattern: /\bMA\s*200\b|\bma200\b|200일선/ },
];

const failures = [];
for (const file of files) {
  const text = readFileSync(join(root, file), "utf8");
  for (const rule of banned) {
    if (rule.pattern.test(text)) {
      failures.push(`${file}: banned ${rule.label}`);
    }
  }
}

if (failures.length > 0) {
  console.error(failures.join("\n"));
  process.exit(1);
}

console.log(`lint ok: ${files.length} TypeScript files checked`);
