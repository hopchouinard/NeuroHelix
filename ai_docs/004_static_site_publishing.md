# Static Site Publishing Specification

## Context
- Current pipeline renders a standalone HTML dashboard per day in `dashboards/` using Bash + inline CSS. Distribution is manual and lacks historical navigation.
- Upcoming requirement is to publish a redesigned, navigable static site powered by Astro, hosted on Cloudflare Pages, and updated automatically after every successful pipeline run.
- The Astro site becomes the canonical source of dashboards; legacy single-file HTML can remain for local fallback but is no longer authoritative.

## Objectives
1. Provide a high-fidelity UI with the new theme (charcoal `#1a1a1a` background, electric violet `#8b5cf6` accents) and structured navigation across the full dashboard history starting from launch day.
2. Automate generation of structured content (metadata, tags, summaries, full markdown) for each day so the static site can ingest it without manual edits.
3. Enable rich discovery: chronological browsing, filters, free-text search over full report content, and tag-based exploration.
4. Publish the built Astro site to Cloudflare Pages on every pipeline execution with zero manual intervention and auditable logs.

## Scope
### In scope
- Scaffold Astro project under `site/` with project-specific design system, components, routing, and build scripts.
- Generate structured data artifacts (`.json` or `.md`) for each day from the existing Bash pipeline.
- Search index generation at build time and client-side consumption (no external services).
- Tag inference per report (mix of explicit report key terms + AI-generated keywords) managed automatically during the pipeline.
- Automated deploy pipeline that runs locally and pushes to Cloudflare Pages via `wrangler` using API tokens.

### Out of scope (initial release)
- Historical backfill before Astro go-live (acceptable to start with the first Astro-powered run).
- Server-side rendering or dynamic APIs beyond Cloudflare Pages hosting.
- Auth / access control (site assumed to be public once published).

## Functional Requirements
1. **Daily ingestion** – Each pipeline run produces a structured payload containing: date, title, executive summary, key themes, sections, strategic actions, raw markdown, permalink slug, and inferred tags.
2. **Navigation** – Site lists dashboards chronologically (newest first) with pagination and jump-to-date control.
3. **Search** – Client-side search over full markdown text using a JSON index generated at build time; results link to sections within a day's page.
4. **Filtering** – Users can filter dashboards by tags (key themes or inferred keywords) and by original research categories (Research/Market/Ideation/etc.).
5. **Detail page** – Each day renders a templated page with redesigned layout, hero summary, metrics, theme cards, chart-ready data placeholders, and raw markdown sections mapped to components.
6. **Canonical hosting** – Cloudflare Pages serves `site/dist`; pipeline ensures successful deployment before marking run complete.

## Non-Functional Requirements
- **Performance**: Lighthouse 90+ at build time, all assets pre-rendered; search index kept under ~2 MB (prune/cap older entries or compress).
- **Reliability**: Deployment step should fail the pipeline if Cloudflare publish fails; logs persisted under `logs/publishing/`.
- **Maintainability**: Configuration-driven data ingestion; minimal hand-edited files under `site/` once scaffolding is done.
- **Observability**: Write publish summary (build duration, bundle size, deploy URL) to logs and optionally to `logs/publishing/latest.json` for quick inspection.

## Solution Architecture
### Directory & Data Layout
```
NeuroHelix/
├── site/                          # New Astro project
│   ├── src/content/dashboards/    # Content collection (one MD/MDX per day)
│   ├── src/data/index.json        # Search index emitted at build time
│   ├── src/data/tags.json         # Tag registry (auto-updated)
│   └── scripts/ingest.mjs         # Converts pipeline payloads into Astro content
├── data/publishing/
│   └── YYYY-MM-DD.json            # Machine-friendly payload generated post-aggregation
└── scripts/renderers/export_site_payload.sh  # Bash helper called by orchestrator
```

### Data Flow
1. Pipeline executes prompts → aggregator builds `daily_report_YYYY-MM-DD.md` as today.
2. New exporter script parses the report, extracts structured blocks, queries Gemini (or deterministic heuristics) for tag suggestions, and emits `data/publishing/YYYY-MM-DD.json`.
3. Astro build script (`pnpm --filter site build`) runs ingestion step that converts all payload files into a content collection and generates a consolidated search index.
4. After successful build, a deploy script runs `npx wrangler pages deploy site/dist --project-name neurohelix-dash --branch production` with Cloudflare API token stored in env.
5. Publish summary appended to logs; orchestration script reports success/failure.

### Tagging Strategy
- Base tags sourced from report headings (e.g., "Model & Technology Advances", "Regulatory"), converted to kebab-case.
- Auto keywords generated daily via Gemini CLI using a lightweight prompt referencing the day's summary; duplicates merged.
- Add a dedicated "Keyword Tag Generator" entry to `config/searches.tsv` so Gemini CLI runs a focused prompt as the final pipeline action before Cloudflare deployment; the script captures the JSON-formatted tag list and feeds it into the payload exporter.
- Tag metadata stored in `data/publishing/YYYY-MM-DD.json` and aggregated into `tags.json` during build for filter controls.

### Search Index
- During `astro build`, run a Node script that loads all dashboard payloads and emits a JSON index containing: date, title, summary snippet, full text (tokenized), tags, and anchored headings. Use Fuse.js or MiniSearch client-side; store only necessary text to keep payload small.

### UI / Styling Notes
- Global background `#1a1a1a`, accent `#8b5cf6`, with complementary neutrals (#f4f4f5, #94a3b8).
- Components: hero summary card, KPI row (domains, token count, generation timestamp), timeline sidebar, tag chips, search panel, section accordions.

### Cloudflare Pages Deployment Methodology
1. **Project setup** – Create Cloudflare Pages project (e.g., `neurohelix-dash`) bound to manual deployments via Wrangler.
2. **Auth** – Generate Cloudflare API token scoped to Pages, store as `CLOUDFLARE_API_TOKEN` in `.env.local` and LaunchD plist (Keychain recommended).
3. **Build** – Use `pnpm --dir site install` (with `PNPM_HOME` cached) followed by `pnpm --dir site build`. Cache `node_modules`, `.astro`, and `site/.wrangler` between runs if possible.
4. **Deploy** – Run `npx wrangler pages deploy site/dist --branch production --commit-hash $(git rev-parse HEAD)` to push the freshly built artifact; capture output URL.
5. **Verification** – Poll `wrangler pages deployment list --project-name ... --limit 1` to confirm status; fail fast if not `ACTIVE`.
6. **Rollback plan** – Keep last successful build artifact (e.g., `site/.deploy-cache/dist_<timestamp>.tar.gz`) to re-deploy quickly if needed.

This approach keeps deploys local (no separate CI) yet produces the same traceability as connecting a repo branch; Wrangler handles asset upload + cache invalidation automatically.

## Pipeline Integration
1. Extend `scripts/orchestrator.sh` to add a new step (`Step 4: Publish static site`).
2. New Bash helper `scripts/renderers/export_site_payload.sh` runs after report generation to create the JSON payload + metadata for Astro.
3. Add `scripts/publish/static_site.sh` which wraps PNPM install/build, search index generation, and `wrangler pages deploy`. This script writes structured logs and returns non-zero on failure.
4. LaunchD job gains environment variables for PNPM, Node, and Cloudflare token; ensure the job PATH includes `~/.npm-global/bin` or similar so `pnpm` and `wrangler` resolve.

## Task Breakdown
| # | Task | Owner | Notes |
|---|------|-------|-------|
|1|Audit existing report sections to define data schema for `data/publishing/*.json`|Research/Eng|Document fields + validation rules|
|2|Implement `export_site_payload.sh` (parse markdown, call Gemini for tags, emit JSON)|Bash/AI|Reuse existing aggregator context|
|3|Scaffold Astro project in `site/` (pnpm create astro, TypeScript, Tailwind optional)|Web|Include ESLint/Prettier|
|4|Configure Astro content collections + ingestion script to load JSON payloads|Web|Generates MD/MDX or direct data|
|5|Design and build UI components with specified theme|Web/Design|Hero, timeline, tag chips, search panel|
|6|Implement client-side search (Fuse.js/MiniSearch) + filters UI|Web|Consume generated index|
|7|Create build-time search index generator script|Web|Triggered via `astro build` hook|
|8|Write Cloudflare deploy script (`publish/static_site.sh`) using Wrangler|DevOps|Handles install/build/deploy/logging|
|9|Update orchestrator + LaunchD plist to include publishing step + env vars|DevOps|Ensure failure propagation|
|10|QA end-to-end: run pipeline, verify site deploy, confirm search/filter/tagging|QA|Document checklist|

## Decisions & Assumptions
1. **Tag generation** – Gemini CLI is the committed solution for daily keyword tags, backed by the new TSV prompt and exporter integration noted above.
2. **Package manager** – `pnpm` is the standard for the `site/` workspace and all tooling/scripts should assume it.
3. **Analytics** – Cloudflare Web Analytics is the chosen measurement platform; include the script snippet during Astro build and surface opt-out settings if needed.
4. **Deployments** – Daily executions publish directly to the production Cloudflare Pages branch; preview deploys are only used during development.

With these decisions locked, implementation can proceed with minimal ambiguity.
