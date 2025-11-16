# AGENTS.md instructions for /Users/pchouinard/Dev/NeuroHelix

<INSTRUCTIONS>
# Repository Guidelines

## Project Structure & Module Organization
- Core automation lives in `scripts/` (Bash orchestrator) and `orchestrator/` (Typer-based Python CLI). Keep CLI modules under `nh_cli/commands`, shared services in `services/`, and configuration schemas beneath `orchestrator/config/`.
- Publishing assets flow from `data/` → `site/`. Markdown reports, manifests, and payloads are generated in `data/publishing` and ingested by `site/scripts/*.mjs` before Astro builds.
- Tests mirror their runtime: Bash smoke tests sit in `/tests`, Python unit and integration suites in `orchestrator/tests`, and frontend artifacts under `site/src` with static assets in `site/public`.

## Build, Test, and Development Commands
- `./scripts/orchestrator.sh` – run the legacy Bash pipeline end-to-end; append flags like `--cleanup-all --dry-run` or `--reprocess-today` for maintenance.
- `cd orchestrator && poetry install && poetry run nh run` – install Python dependencies and execute the modern orchestrator. Use `poetry run nh diag` for environment checks.
- `cd orchestrator && poetry run pytest` – preferred unit/integration suite with coverage (`pytest -v --cov`).
- `cd site && pnpm prebuild && pnpm dev` – regenerate Astro content then start the local UI. `pnpm build` and `pnpm preview` mirror the Cloudflare Pages flow, while `pnpm astro check` validates content collections.

## Coding Style & Naming Conventions
- Python uses type hints everywhere, 100-character lines, and `black`, `ruff`, plus `mypy --strict`; follow `snake_case` for functions, `PascalCase` for services, and keep Typer commands in files named after their verb (`run.py`, `registry.py`).
- Bash scripts should start with `#!/usr/bin/env bash` and `set -euo pipefail`, keep functions in `snake_case`, and store shared helpers under `scripts/lib/` for reuse.
- Astro/TypeScript files live under `site/src`; keep components `PascalCase.astro`, co-locate style tokens in `src/styles`, and prefer named exports in `.ts` helpers.

## Testing Guidelines
- Python orchestrator: target ≥90% coverage by default; tests belong in `orchestrator/tests/unit` or `.../integration` and follow `test_<subject>.py` naming. Use fixtures in `tests/fixtures` to isolate registry/data dependencies.
- Bash pipeline: run `./tests/test_telemetry.sh` (full pipeline), `test_context_aware_prompts.sh`, or the narrower scripts before merging runtime changes.
- Frontend ingest/search changes require `pnpm prebuild && pnpm astro check` and spot-checking the generated dashboards via `pnpm dev`.

## Commit & Pull Request Guidelines
- Follow Conventional Commits as seen in history (`feat:`, `docs:`, `chore:`, etc.) and describe the scope briefly (e.g., `feat: add sqlite registry provider`).
- Each PR should explain the motivation, list affected subsystems (Bash orchestrator, Python CLI, site), link to any dashboards/tests, and attach screenshots or terminal output when UI/tests change.
- Ensure branches are rebased onto `main`, CI passes `pytest` + Bash tests + `pnpm build`, and configuration secrets (any `.env*` files) are excluded from commits.

## Security & Configuration Tips
- Keep API tokens and Gemini credentials in `config/env.sh` or `.env*` files; never hardcode secrets in scripts, Astro envs, or manifests.
- Use `nh config validate` (Python) or `./scripts/orchestrator.sh --dry-run` (Bash) before deploying changes to confirm schema compatibility and safe file operations.
- Review generated artifacts in `data/` for sensitive content before publishing to Cloudflare Pages or committing sample outputs.
</INSTRUCTIONS>
