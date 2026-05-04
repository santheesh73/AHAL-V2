import { cpSync, existsSync, mkdirSync, rmSync, writeFileSync } from "node:fs"
import { dirname, join, resolve } from "node:path"
import { fileURLToPath } from "node:url"

const __dirname = dirname(fileURLToPath(import.meta.url))
const root = resolve(__dirname, "..")
const outputDir = join(root, "demo-package")
const distDir = join(root, "dist")

if (!existsSync(distDir)) {
  throw new Error("Build output not found. Run `npm run build` before packaging the public demo bundle.")
}

rmSync(outputDir, { recursive: true, force: true })
mkdirSync(outputDir, { recursive: true })

cpSync(distDir, join(outputDir, "dist"), { recursive: true })

for (const file of ["README.md", "QA_CHECKLIST.md", "DEMO_CHECKLIST.md", "PUBLIC_DEMO_PROMPT.md"]) {
  cpSync(join(root, file), join(outputDir, file))
}

const manifest = {
  package: "AHAL AI Frontend v2 Public Demo",
  generatedAt: new Date().toISOString(),
  entry: "dist/index.html",
  backendUrl: "http://localhost:8000",
  commands: {
    backend: 'cd "C:\\Users\\babus\\OneDrive\\Desktop\\AHAL v2" && python -m app.main',
    frontend: 'cd "C:\\Users\\babus\\OneDrive\\Desktop\\AHAL v2\\frontend" && npm run dev',
    build: "npm run build",
    package: "npm run package:demo",
  },
  regressionCriteria: [
    "Do not display content management application when explicit metadata says developer tool.",
    "Do not show MongoDB as a language.",
    "Do not duplicate POST /analyze or GET /status variants.",
    "Do not show types/index.ts initializes FastAPI.",
    "Do not show long nested paths in primary UI.",
    "Do not expose .env.example or raw mongodb:// evidence in primary UI.",
    "Test gap, onboarding, repo index, delta scan, chat, and downloads must remain reachable from dashboard.",
  ],
}

writeFileSync(join(outputDir, "demo-manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`)

console.log(`Public demo package written to ${outputDir}`)
