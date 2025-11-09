# NeuroHelix Source Layout & Publishing Specification

## Context
- Builds directly on the Astro site, ingestion flow, and deployment automation defined in `004_static_site_publishing.md`.
- Expands the daily publishing system so every synthesized report ships with an IDE-inspired dual view: *Processed View* (rich markdown rendering) and *Source View* (raw artifacts exactly as generated under `data/outputs/daily/YYYY-MM-DD/`).
- The UX must evoke GitHub’s “Preview | Code” tabs without impersonating an editor; processed content gets polished presentation while raw files retain their original names, folder hierarchy, and encoding.

## Objectives
1. Ship a cohesive layout that keeps the hero toolbar, sidebar, reading pane, and table-of-contents synchronized across both views.
2. Expose every intermediate artifact (prompts, summaries, cross-analysis, insight drafts, future file types) alongside the synthesized report with zero renaming or content mutation.
3. Extend the pipeline + Astro build so selective rebuilds (`--day YYYY-MM-DD`) populate both processed and raw assets idempotently.
4. Power a unified command palette + global search that spans synthesized narratives and every raw document.
5. Produce machine-readable metadata and JSON exports suitable for future vector ingestion without adding new external dependencies.

## Scope
### In Scope
- Layout, routing, components, and styling for the two-view experience inside the existing Astro project.
- Pipeline updates that copy raw artifacts, emit new manifests, and feed Astro content collections/search indices.
- Navigation primitives: repo-style sidebar, collapsible folders, breadcrumbs, TOC, command palette coverage.
- Meta index page listing all published days with a repo/file-tree metaphor.
- Theme toggle (light/dark) plus new electric-violet highlight tokens for IDE affordances.
### Out of Scope
- Restating Astro scaffolding, Cloudflare deployment, or search infrastructure already covered in earlier specs (reuse as-is).
- Authentication, role-based visibility, or authoring tools.

## Experience Overview
- **Processed View (default)** mirrors GitHub’s “Preview” tab: synthesized daily report rendered in the main pane with typography, hero toolbar, summary cards, and TOC.
- **Source View** mirrors GitHub’s “Code” tab: left sidebar shows a repo-like tree rooted at the selected day; clicking files renders their raw contents in the reading pane with syntax highlighting and metadata.
- Persistent top toolbar houses date selector, view toggle, command palette launcher, and context CTA.
- Hero background + toolbar remain charcoal with violet hover/active accents; hover highlight on sidebar rows uses an electric-violet glow (`box-shadow: 0 0 0 1px #8b5cf6 inset`).

## Functional Requirements
1. **Dual-Layer Publishing & View Toggle**
   - Toggle buttons labeled `Processed View` and `Source View` live in the hero toolbar; keyboard shortcut `Shift+P` toggles processed, `Shift+S` toggles source.
   - Toggle state persists per session (localStorage key `nh:viewMode`) and is reflected via query param `?view=processed|source` for deep links.
   - Re-render only the main content region when switching; sidebar + toolbar persist.
2. **Directory-Style Source Navigation**
   - Each day appears as a repo root; folder names match the on-disk directories under `data/outputs/daily/YYYY-MM-DD/`.
   - Collapsible nodes, file icons by extension (Markdown, JSON, txt, csv, png fallback).
   - Hover highlight in electric violet; active file uses filled accent background.
   - Sidebar supports type filtering chips (e.g., Prompts, Summaries, Cross-Analysis, Drafts, Other) derived from metadata but never renames files.
3. **Layout & Visual Design**
   - Persistent hero toolbar with background image (reused from spec 003) and context actions (date navigation, publish status, share button).
   - Three-panel responsive layout:
     - Sidebar (IDE explorer) collapsible on ≤1024px.
     - Main reading pane with constrained line length (~72ch) and center alignment.
     - Auxiliary pane (optional on ≥1280px) for TOC, metadata, or search results.
   - Command palette reuses existing component but now indexes raw artifacts; accessible via `⌘K`/`Ctrl+K`.
   - Light/dark toggle anchored in toolbar; tokens defined under `site/src/styles/tokens.css`.
4. **Raw Data Rendering**
   - Route pattern: `/daily/[date]/source/<encodedPath>` maps 1:1 to files living under `data/outputs/daily/[date]/`.
   - Breadcrumb shows `Daily Reports / YYYY-MM-DD / path/to/file.md` with link back to processed view.
   - File header displays:
     - Relative path
     - File size + checksum (sha256 short hash)
     - Artifact type (prompt, summary, cross-analysis, etc.)
     - Origin metadata (prompt id, timestamp)
   - Markdown rendered via Astro Markdown/MDX; non-markdown falls back to code viewer with syntax detection via Shiki (JSON, YAML, text).
   - Download button streams the exact file content.
5. **Command Palette & Global Search**
   - Search index aggregates:
     - Processed report fields (title, sections, headings, summaries).
     - Raw artifact metadata + text content (capped at 200KB per file to avoid huge payloads).
   - Results grouped: `Processed` vs `Source`; hitting Enter navigates accordingly.
   - Palette indicates file type, path, and matched snippet; respects theme toggle.
6. **Table of Contents & Outline View**
   - Processed View TOC anchors to headings; Source View TOC becomes file-level metadata (e.g., list of headings inside selected Markdown or sections derived from JSON keys).
7. **Meta Index Page**
   - `/source` lists every published day as expandable folders showing top-level directories/files for each day (lazy loaded via manifest).
   - Provides filters for date range, artifact type, and publish status.
8. **Idempotent & Selective Rebuilds**
   - Rebuilding a specific day with existing orchestrator flag `--day YYYY-MM-DD` regenerates the synthesized payload, source manifest, and Astro content for that day only.
   - Pipeline must never mutate other days’ manifests or raw file copies when re-running.
9. **Accessibility & Performance**
   - Sidebar, TOC, and view toggles fully keyboard navigable; focus rings align with theme tokens.
   - Lazy-load file contents only when requested; large JSON >1 MB stream chunked with virtualized viewer.

## Data Contracts & Content Artifacts
The existing `data/publishing/YYYY-MM-DD.json` remains the canonical processed payload. Add the following companion artifacts:

1. **`data/publishing/source_manifests/YYYY-MM-DD.json`**
   ```json
   {
     "date": "2025-01-05",
     "root": "data/outputs/daily/2025-01-05",
     "generatedAt": "2025-01-05T09:12:44Z",
     "artifacts": [
       {
         "relativePath": "research/prompts/prompt_01.md",
         "artifactType": "prompt",
         "displayGroup": "Research",
         "sizeBytes": 1824,
         "checksum": "a9b3f2...",
         "createdAt": "2025-01-05T07:55:02Z",
         "sourcePromptId": "research_alignment_v3",
         "mime": "text/markdown",
         "tags": ["prompt", "research"],
         "toc": [
           { "text": "Objective", "hash": "#objective" },
           { "text": "Constraints", "hash": "#constraints" }
         ],
         "preview": "Model alignment risks in multi-agent chains..."
       }
     ],
     "stats": {
       "artifactCount": 42,
       "byteSize": 837211,
       "types": { "prompt": 5, "summary": 8, "cross_analysis": 6, "insight_draft": 4, "other": 19 }
     }
   }
   ```
2. **`data/publishing/source_blobs/YYYY-MM-DD/<relativePath>`**
   - Exact copies of the raw files, preserving directory structure.
   - Stored under `site/static/source/YYYY-MM-DD/...` during build for direct serving/download.
3. **Generic Schema Forward-Compatibility**
   - `artifactType` accepts known enum values (`prompt`, `raw_summary`, `cross_analysis`, `insight_draft`, `metadata`, `other`) but pipeline may append new types; UI treats unknown types as `other` while still using provided `displayGroup`.
   - Optional `extensions` object allows future metadata (vector embedding ids, citations).
4. **Vector Metadata Export**
   - Build `data/publishing/vector_exports/YYYY-MM-DD.json` referencing artifact IDs, embeddings (if available), and content hashes to satisfy the “JSON metadata export” requirement.

### Data Contract Notes
- Manifests should be deterministic; sort `artifacts` by `relativePath`.
- `toc` array optional; populated only when parser can extract headings (Markdown/JSON keys).
- `preview` trimmed to 280 chars; sanitized to prevent HTML injection (render as plaintext).

## Pipeline & Build Changes
1. **Raw Artifact Collection**
   - New bash helper `scripts/renderers/export_source_manifest.sh` runs after report synthesis:
     1. Walk `data/outputs/daily/<date>/`.
     2. Capture metadata (size, checksum, timestamps).
     3. Detect artifact type via folder heuristics + filename patterns.
     4. Generate manifest JSON + `vector_exports`.
     5. Sync files into `site/static/source/<date>/` (rsync) for Astro consumption.
2. **Selective Rebuild Integration**
   - Extend existing orchestrator flag `--day YYYY-MM-DD` to call:
     - `export_site_payload.sh` (already exists per spec 004).
     - `export_source_manifest.sh`.
     - `pnpm --dir site build --filter daily:<date>` (Astro content collection limited by date env var) to avoid rebuilding all days when unnecessary.
3. **Astro Content Ingestion**
   - Enhance `site/scripts/ingest.mjs` to ingest both `daily.json` payloads and `source_manifests`.
   - Create a `SourceArtifact` content collection storing metadata only; raw file contents served from static copies to keep build size manageable.
4. **Search Index Generation**
   - Update build step that emits `site/src/data/search-index.json` to include:
     - Each artifact’s metadata + truncated body (read from file when ≤200KB; otherwise stub with metadata only).
     - Flags for `scope: "processed" | "source"`.
5. **Logging & Idempotency**
   - Append manifest generation summary to `logs/publishing/YYYY-MM-DD.log`.
   - On rebuild, existing static files/manifests replaced atomically (write temp, rename).

## Astro Implementation Plan
### Directory Layout Additions
```
site/
├── src/components/source/
│   ├── ViewToggle.astro
│   ├── FileTree.tsx
│   ├── ArtifactHeader.astro
│   ├── RawViewer.tsx
│   └── CommandPaletteResults.tsx
├── src/layouts/DailyLayout.astro        # extended to host dual views
├── src/pages/daily/[date]/index.astro   # Processed view wrapper
├── src/pages/daily/[date]/source/[...path].astro
├── src/pages/source/index.astro         # meta index
├── src/data/source-manifests/*.json     # generated at build
└── static/source/YYYY-MM-DD/**          # raw files
```

### Key Components & Responsibilities
- `ViewToggle`: renders buttons, handles keyboard shortcuts, syncs query params/localStorage.
- `Toolbar`: extend existing hero toolbar to include view toggle, theme toggle, search button, rebuild status indicator.
- `FileTree`: virtualized tree with collapsible folders, type filter chips, search within tree.
- `ArtifactHeader`: displays breadcrumbs, metadata chips, download button, share link.
- `RawViewer`: lazy-loads file content; chooses renderer (Markdown, code block, JSON inspector, binary placeholder).
- `CommandPalette`: extend to fetch results from combined search index and support arrow navigation between processed/source groups.
- `TocPanel`: context-aware (processed headings vs artifact headings).

### State Management
- Use a lightweight signal/store (e.g., `@nanostores` or Astro Islands with React/Svelte) to synchronize:
  - Current view mode.
  - Selected file path + metadata.
  - Tree expansion state.
  - Active filters/search query.
- Persist tree + selected view per date to localStorage for continuity.

## Routing & Navigation Rules
1. `/daily/[date]/` → processed view (default). Accepts `?view=source` which deep-links to the same slug but auto-switches view mode.
2. `/daily/[date]/source/[...path]` → source file detail; server-side loads manifest entry + streams file content.
3. `/source` → meta index (list of days).
4. Command palette entries use canonical URLs above; copying share link should include `view` param or file path.

## Search & Command Palette Behavior
- Search index stored under `site/src/data/search-index.json` with entries:
  ```
  {
    "id": "2025-01-05::source::research/prompts/prompt_01.md",
    "date": "2025-01-05",
    "scope": "source",
    "title": "prompt_01.md",
    "path": "research/prompts/prompt_01.md",
    "artifactType": "prompt",
    "snippet": "Model alignment risks...",
    "tokens": "model alignment risks ...",
    "tags": ["prompt","research"]
  }
  ```
- Fuse.js/MiniSearch configuration should treat `scope`, `tags`, and `path` as searchable fields.
- Palette groups first by scope, then by date; arrow keys cycle, `Enter` navigates, `Cmd+Enter` opens in new tab.

## Layout & Styling Guidelines
- Tokens: extend `tokens.css` with IDE-specific variables (`--color-sidebar`, `--color-highlight`, `--color-hover-violet`, `--font-mono`).
- Sidebar uses monospaced labels; main pane uses Inter/SF per existing spec.
- Table-of-contents panel uses subtle separators and scrollspy to highlight in-view heading/file section.
- Light mode mirrors same structure with updated neutrals (#f9fafb background, #1f2937 text) while preserving electric violet accent.

## Accessibility, Performance, Maintenance
- Keyboard support: arrow navigation inside tree, `Enter` to open, `Space` to expand/collapse, `Cmd/Ctrl+F` focuses sidebar search.
- Focus outlines must meet 3:1 contrast; provide skip-to-content link for screen readers.
- Performance budget: initial page load ≤200KB JS; tree + raw viewer islands code-split; raw file fetch streaming with `ReadableStream`.
- Unit tests (Vitest) for manifest parser + path resolver; UI smoke tests using Playwright to ensure toggles + navigation behave as intended.

## Deployment & Telemetry
- No new infrastructure; reuse Cloudflare Pages deployment from spec 004.
- Add telemetry hooks (optional data attributes) for:
  - View toggle usage
  - Command palette search queries (hashed)
  - Raw file downloads
- Log selective rebuild operations to `logs/publishing/source_view.json` for traceability.

## Task Breakdown

| # | Task | Owner | Notes |
|---|------|-------|-------|
|1|Implement `export_source_manifest.sh` + vector export|Pipeline|Derive artifact types, emit manifest + copy raw files|
|2|Extend ingestion script + content collections for manifests|Web/Pipeline|Ensure deterministic sorting + schema validation|
|3|Enhance search index generator to include source artifacts|Web|Capture snippets + scope tags|
|4|Build toolbar view toggle + theme toggle integration|Frontend|Keyboard shortcuts + persisted state|
|5|Implement FileTree component with filters + lazy loading|Frontend|Virtualized list for >200 files|
|6|Create RawViewer + ArtifactHeader + breadcrumb flow|Frontend|Supports Markdown, JSON, text, binary placeholder|
|7|Update CommandPalette to show processed + source results|Frontend|Group rendering + navigation|
|8|Add `/daily/[date]/source/[...path]` and `/source` routes|Frontend|Server load manifest entries + static files|
|9|Design meta index page + repo-style listing|Frontend|Aggregates stats per day|
|10|QA selective rebuild pipeline + end-to-end nav/search|QA|Test `--day` flag, idempotency, accessibility|

## Risks & Mitigations
- **Large Raw Files**: Limit inline rendering to ≤2 MB; provide download-only banner for larger binaries. Mitigation: streaming + size guard.
- **Manifest Drift**: If files change between manifest generation and Astro build, paths may desync. Mitigation: copy raw files immediately after manifest creation and hash-verify during build.
- **Search Payload Size**: Including every raw file could bloat index. Mitigation: truncate text at 10 KB per file and rely on metadata for the rest.
- **Accessibility Debt**: Complex tree interactions risk inaccessible UX. Mitigation: reuse ARIA patterns from WAI-ARIA Authoring Practices for treeviews.

## Open Questions
1. Should raw binary artifacts (images, CSVs) be previewed inline via dedicated viewers, or restricted to download-only?
   - Restrict to download-only for simplicity and performance; inline viewers can be added in future iterations if needed.
2. Do we need retention policies for raw artifacts (e.g., prune after N days) to keep Cloudflare storage lean, or is indefinite hosting acceptable?
   - Indefinite hosting is acceptable for now given current storage limits; revisit if usage patterns change significantly.
