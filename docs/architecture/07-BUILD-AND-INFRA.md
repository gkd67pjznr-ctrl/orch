# Build Infrastructure & DevOps

## Build Pipeline

### Build Order (strictly sequential)

```
tui → ai → agent → coding-agent → mom → web-ui → pods
```

Not parallelizable — TypeScript path aliases require earlier packages compiled first.

### Key Commands

```bash
npm install          # Install all dependencies
npm run build        # Sequential build (all packages)
npm run check        # biome check + tsgo --noEmit + browser-smoke + web-ui check
npm test             # Run tests across all workspaces
./test.sh            # Run tests WITHOUT API keys (safe for CI)
./pi-test.sh         # Run pi CLI from sources (dev)
```

---

## TypeScript Configuration

### Base Config (`tsconfig.base.json`)

```json
{
  "target": "ES2022",
  "module": "Node16",
  "moduleResolution": "Node16",
  "declaration": true,
  "declarationMap": true,
  "sourceMap": true,
  "strict": true,
  "experimentalDecorators": true,
  "emitDecoratorMetadata": true
}
```

### Path Aliases (`tsconfig.json`)

```
@mariozechner/pi-ai        → packages/ai/src/index.ts
@mariozechner/pi-agent-core → packages/agent/src/index.ts
@mariozechner/pi-tui        → packages/tui/src/index.ts
@mariozechner/pi-coding-agent → packages/coding-agent/src/index.ts
@mariozechner/pi-web-ui     → packages/web-ui/src/index.ts
@mariozechner/pi-mom        → packages/mom/src/index.ts
@mariozechner/pi            → packages/pods/src/index.ts
```

### Compiler

Uses `tsgo` (TypeScript native preview) for type checking: `@typescript/native-preview 7.0.0-dev.20260120.1`

---

## Linting & Formatting (Biome)

```json
{
  "formatter": {
    "indentStyle": "tab",
    "indentWidth": 3,
    "lineWidth": 120
  },
  "linter": {
    "rules": {
      "style.noNonNullAssertion": "off",
      "style.useConst": "error",
      "suspicious.noExplicitAny": "off"
    }
  }
}
```

**Note**: Tab indentation with 3-space visual width (unusual).

---

## Binary Compilation (`scripts/build-binaries.sh`)

### Platforms

darwin-arm64, darwin-x64, linux-x64, linux-arm64, windows-x64

### Process

1. Install all cross-platform native bindings (clipboard, sharp) with `--force`
2. Build all packages
3. For each platform: `bun build --compile --external koffi --target=bun-$platform`
4. Copy assets: package.json, WASM, themes, export-html templates, docs, examples
5. Archive: tar.gz (Unix, wrapped in `pi/` dir for mise) or zip (Windows)

**Key**: koffi externalized because it has 18 platform-specific .node files (~74MB total).

---

## CI/CD Workflows

### ci.yml (push/PR to main)

Ubuntu latest, Node.js 22. Installs system deps (libcairo, pango, etc.), runs build + check + test.

### build-binaries.yml (v* tags)

Triggered on version tag push. Builds all platform binaries, extracts changelog, creates GitHub Release with artifacts.

### pr-gate.yml (PR opened)

Strict contributor approval: checks APPROVED_CONTRIBUTORS file or write+ access. Auto-closes unapproved PRs.

### approve-contributor.yml (issue comment)

Listens for `lgtm` from write+ collaborators, adds to APPROVED_CONTRIBUTORS, commits.

### oss-weekend-issues.yml (issue opened)

During OSS weekend (configured in .github/oss-weekend.json), auto-closes issues from non-approved contributors.

---

## Release Process (`scripts/release.mjs`)

### Lockstep Versioning

ALL packages always share the same version number. `scripts/sync-versions.js` enforces this.

### Semantics

- `patch`: Bug fixes and new features
- `minor`: API breaking changes

### Steps

1. Check for uncommitted changes
2. Bump version: `npm run version:${type}` (updates all packages)
3. Update CHANGELOGs: replace `## [Unreleased]` with `## [version] - date`
4. Commit and tag: `git commit -m "Release v${version}"` + `git tag v${version}`
5. Publish to npm: `npm run publish`
6. Add new `## [Unreleased]` sections
7. Commit changelog updates
8. Push main + tag

---

## Pre-commit Hook (`.husky/pre-commit`)

1. Run `npm run check` (biome + tsgo + browser-smoke + web-ui)
2. If staged files include ai/, web-ui/, package.json → also run browser smoke test (ESBuild)
3. Re-stage any files modified by biome formatting
4. Fail if any check fails

### Browser Smoke Test

ESBuild compiles `scripts/browser-smoke-entry.ts` to validate pi-ai can be bundled for browsers.

---

## Project Configuration (.pi/)

### Extensions

| File | Purpose |
|------|---------|
| `.pi/extensions/diff.ts` | Git diff view with VS Code integration |
| `.pi/extensions/files.ts` | List files read/written/edited in session |
| `.pi/extensions/tps.ts` | Tokens-per-second metrics |
| `.pi/extensions/prompt-url-widget.ts` | GitHub PR/issue URL detection |

### Prompt Templates

| File | Purpose |
|------|---------|
| `.pi/prompts/cl.md` | Changelog audit before release |
| `.pi/prompts/is.md` | Analyze GitHub issues |
| `.pi/prompts/pr.md` | Review GitHub PRs |
| `.pi/prompts/wr.md` | Wrap up: changelog + commit + push |

---

## Profiling (`scripts/profile-coding-agent-node.mjs`)

```bash
npm run profile:tui     # TUI startup timing
npm run profile:rpc     # RPC startup timing
```

Measures startup phases: parseArgs, runMigrations, createResourceLoader, resolveModelScope, createSessionManager, createAgentSession, interactiveMode.init, initTheme.

## Cost Analysis (`scripts/cost.ts`)

```bash
npx tsx scripts/cost.ts -d ~/my-project -n 7
```

Analyzes LLM usage costs from session logs. Groups by day and provider with input/output/cache token breakdowns.

---

## Key Infrastructure Quirks

1. **Build order not enforced by tooling**: Manual ordering in package.json build script
2. **Binary compilation requires Bun**: Not Node.js (Bun compile for cross-platform binaries)
3. **Contributor approval gate strict**: AI-generated low-quality PRs prevention
4. **No CI publishing**: npm publish runs locally in release.mjs, not in GitHub Actions
5. **Biome 3-space tab width**: Unusual formatting choice, enforced by --write flag
6. **Browser smoke test on pre-commit**: Ensures pi-ai remains browser-bundleable
