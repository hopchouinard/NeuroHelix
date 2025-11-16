# Scratchpad for Neurohelix Site Implementation

Key questions to unblock implementation
1) Cloudflare setup
•  Project name: neurohelix-site. Is the Cloudflare Pages project name I want.
•  Domain: The real production domain is neurohelix.patchoutech.com.
•  API token: I confirm that I will create a Cloudflare API token with Pages permissions. Preferred storage:
◦  Stored in a .env.local (kept out of git) and referenced by the deploy script.

2) Runtime toolchain
•  Node version: Standardize on Node 24.x LTS
•  Package manager: The spec standardizes pnpm and it is already installed.
•  Wrangler: Install wrangler (locally in site/ devDependencies) and run via npx

3) Prompt addition for tag generation
•  We’ll add a new, enabled row to config/searches.tsv named Keyword Tag Generator. I am OK with the following JSON-only output contract for easy ingestion
◦  Output strictly in JSON with fields: { "tags": string[], "categories": string[] } where tags are 1–3-word keywords and categories map to your existing report theme buckets.

4) Deployment behavior
•  Idempotency: Reruns on the same day skip regenerating payload if data/publishing/YYYY-MM-DD.json exists and report hasn’t changed, but still attempt deploy (so I can force-redeploy via a flag)
•  Failure policy: If Cloudflare deploy fails, should the orchestrator exit non-zero and mark the day as failed? (Yes)

5) Search and UI scope
•  For initial release, OK to implement:
◦  A clean theme (charcoal #1a1a1a background, violet #8b5cf6 accents),
◦  Chronological list, day detail pages, tag filter chips, and client-side search (MiniSearch),
◦  Basic KPI row and hero summary,
◦  No historical backfill (start from launch date going forward).

## NeuroHelix new features

Please improve the site rendering of the source markdown reports by implementing the following features:
1. Tag Cloud: Display a tag cloud on the dashboard page showing all unique tags from reports
2. Search Functionality: Implement a client-side search bar to filter reports by keywords in title and content
3. Category Filters: Add filter buttons to view reports by category (e.g., AI Trends, Market Analysis)
4. Make sure to have CSS styles for all the markdown elements used in the reports (headings, lists, code blocks, etc.) for consistent rendering.
   - Use a clean, modern font like fira code for better readability.
   - Use the standard markdown rendering styles of GitHub or similar platforms as a reference.
5. Ensure proper spacing and alignment for all elements to enhance visual hierarchy.
6. Include a footer with copyright information and links to NeuroHelix social media or contact pages.
7. Include a Hero Section at the top of the dashboard with a brief description of NeuroHelix and its mission and make it visually appealing with a background image.
8. This feature is critical for user engagement and content discoverability on the NeuroHelix platform.

## Answers to clarifying questions

1. Hero Image: The spec mentions a hero background image (site/src/assets/hero.jpg). Should I:
  - Include a placeholder image creation/selection task for now
2. Social Links: The spec asks for Twitter/X, LinkedIn, and GitHub links in the footer. Should I:
  - Use (<https://x.com/patchoutech>) for Twitter/X
  - Use (<https://www.linkedin.com/in/patrickchouinard/>) for LinkedIn
  - Use the real GitHub link (<https://github.com/hopchouinard/NeuroHelix>) for GitHub
3. Categories: Looking at the sample data, I see the categories field is empty in the current dashboard JSON. Should the implementation:
  - Derive categories from existing tags
4. Font Loading: Should I:
  - Use Fontsource packages for Fira Code and Inter
5. Syntax Highlighting: Choose the one that integrates best with Astro
6. Analytics: Included in the initial implementation

## NeuroHelix new features - continued

This new feature will address the prompt pipeline management and execution monitoring for NeuroHelix.

1. The prompt in the categories other than "Analysis" can all be performed in parallel. Only the "Analysis" category prompt needs to be executed after all other prompts are completed.
2. Prompt in the "Analysis" category will take as input the outputs of all other prompts executed that day and need to be run in sequence after all other prompts are done.
3. The prompt "Keyword Tag Generator" should be executed last and categorized as "Analysis" since it needs to analyze the entire daily report to extract relevant tags and categories.
4. The prompts in the "Meta" category have to be executed last after all the others since they are generating summary and strategic implication sections based on the full report and should mention where their outputs are located in the report.
5. The orchestrator script should log the start and end time of each prompt execution, along with any errors encountered, to a daily log file located at logs/prompt_execution_YYYY-MM-DD.log.
6. The prompt execution status (success/failure) should be recorded in a summary section at the end of the daily report for easy reference.
7. If any prompt fails during execution, the orchestrator should continue executing the remaining prompts but mark the failed ones in the summary section of the report.
8. The orchestrator should send an email notification to the admin (<chouinpa@gmail.com>) if any prompt fails, including details of the failure from the log file.

### Answering clarifying questions

## Open Questions Answers
1. Remain unordered beyond parallelization constraints.
2. Single attempt sufficient for now.
3. Batched summary at the end of the run.
4. Daily report summary include execution durations.

### answering clarifying questions for the new layout specification.

1. Should it cover both the Astro layout implementation and the upstream pipeline/publishing changes (data export, routing, selective rebuild tooling), or focus strictly on the front-end experience?
   - It should cover both the Astro layout implementation and the upstream pipeline/publishing changes to ensure a cohesive user experience. This specification should detail how the front-end will interact with the data provided by the pipeline, as well as any necessary changes to the publishing process to support the new layout.
2. Do you expect explicit technical decisions (e.g., component structure, data contracts, deployment hooks) similar to the earlier specs in ai_docs/00x_*.md, or a lighter-weight brief? 
   - I expect explicit technical decisions similar to the earlier specs. This should include detailed component structures, data contracts, and deployment hooks to ensure clarity and ease of implementation for the development team.

Please make sure to ask any clarifying question necessary to make absolutely certain your understanding is complete. 

---

1. Should I assume the Astro site from 004_static_site_publishing.md already exists and this spec layers on top of that foundation, or do you want me to restate any prerequisites from 004 so the document can stand on its own?
   - Assume the Astro site from 004_static_site_publishing.md already exists. This specification should build upon that foundation without restating prerequisites, allowing for a focused approach on the new layout and publishing changes.
2. For the “Source View,” do you want raw files surfaced exactly as they exist in data/outputs/daily/YYYY-MM-DD/ (same file names, folders), or should the spec describe any normalization/renaming before publishing?
   - This function should behave the same way as "Preview | Code" View in GitHub, so raw files should be surfaced exactly as they exist in data/outputs/daily/YYYY-MM-DD/ without any normalization or renaming before publishing. The “Processed View" should handle any necessary rendering or formatting and represent what the "Preview" tab does on GitHub and the "Source View" should represent what the "Code" tab does on GitHub.
3. When defining the data contracts: do we need to account for every artifact type we expect today (prompts, summaries, cross-analysis, etc.) or leave room for arbitrary future file types with a generic schema?
   - We should account for every artifact type we expect today to ensure proper rendering and navigation. However, the schema should also be designed to accommodate arbitrary future file types, allowing for flexibility and scalability in the publishing system.
4. Selective rebuilds: should the spec mandate a new CLI (e.g., ./scripts/publish.sh --day 2025-01-02 --view source) or integrate into the existing orchestrator flags described in earlier specs?
   - The spec should integrate into the existing orchestrator flags described in earlier specs. This approach will maintain consistency in the deployment process and minimize the need for additional tooling, making it easier for developers to manage builds and deployments.
5. Command palette/global search: should the new index cover both synthesized reports and raw source files, or only the synthesized layer?
   - The new index should cover both synthesized reports and raw source files. This comprehensive search functionality will enhance user experience by allowing users to easily find information across all layers of the published content.

---

## Python vs bash features comparison

| Capability | Bash implementation | Python implementation | Parity? |
  | - | - | - | - |
  | Daily pipeline run | ./scripts/orchestrator.sh always runs all shell stages (prompt executor, aggregators, tag extraction, dashboard, export, publish, notifications) in order (scripts/orchestrator.sh:301-351). | nh run executes prompt “waves” with manifests, locking, retries, and telemetry (orchestrator/nh_cli/commands/run.py:23-254, services/runner.py:1-120). It covers prompt execution/export but doesn’t call the legacy
  shell aggregators/renderers. | ⚠️ Comparable core run capability, but Python replaces downstream shell stages with new manifest-driven waves and omits the built-in publish/notifier steps. |
  | Selective waves / force reruns | Bash pipeline has no flags to limit steps; runs everything each time (scripts/orchestrator.sh:299-351). | nh run --wave/--force lets operators rerun a single wave or prompt (orchestrator/nh_cli/commands/run.py:31-150). | ➕ Python-only enhancement (useful for parity testing or partial reruns). |
  | Workspace cleanup | ./scripts/orchestrator.sh --cleanup-all wipes predefined paths, enforces git safety, and logs Cloudflare context (scripts/orchestrator.sh:94-160, scripts/lib/cleanup.sh:1-120). | nh cleanup deletes stale locks/artifacts with retention, dry-run, JSON output and audit logging (orchestrator/nh_cli/commands/cleanup.py:16-239). | ⚠️ Mostly equivalent. Python gains retention + reporting, while Bash still
  performs git checks and Cloudflare coordination (see below). |
  | Cloudflare retraction during cleanup | After cleanup Bash inspects Cloudflare deployments and records the ID for rollback tracking (scripts/orchestrator.sh:148-153, scripts/lib/cloudflare.sh:1-93). | nh cleanup never hits Cloudflare APIs (orchestrator/nh_cli/commands/cleanup.py). | ❌ Missing in Python; Bash remains the only path that documents deployment context during wipes. |
  | Force reprocess of today | Bash mode deletes today’s artifacts, can terminate a running pipeline via --allow-abort, and tags the rerun as a manual override (scripts/orchestrator.sh:168-367, scripts/lib/reprocess.sh:1-180). | nh reprocess simply delegates to nh run --date and assumes artifacts already exist; it can’t terminate active runs or clear data first (orchestrator/nh_cli/commands/reprocess.py:17-107). | ⚠️ Partial
  parity; Python reruns logic but lacks the cleanup/abort safeguards of the Bash flow. |
  | Failure notifications & success pings | Bash optionally calls scripts/notifiers/notify_failures.sh and scripts/notifiers/notify.sh behind env flags (scripts/orchestrator.sh:313-351). | nh run only enumerates waves through WaveType.EXPORT (orchestrator/nh_cli/commands/run.py:127-134) and has no notifier integration. | ❌ Feature only exists in Bash today. |
  | Static site publishing | Bash automatically publishes during Step 5 when ENABLE_STATIC_SITE_PUBLISHING is true (scripts/orchestrator.sh:333-350). | Publishing is a dedicated command (nh publish) that wraps the same scripts/publish/static_site.sh and logs audit info (orchestrator/nh_cli/commands/publish.py:17-128). nh run does not call it by default. | ⚠️ Both can deploy, but Python requires a separate command or manual
  wave call, so end-to-end parity needs human coordination. |
  | Automation install & management | Shell scripts install_automation.sh / uninstall_automation.sh generate and load the LaunchD plist, but offer no status view (install_automation.sh:1-104). | nh automation install/status/remove covers generation, launchctl calls, status reporting, and audit logging (orchestrator/nh_cli/commands/automation.py:1-210). | ✅ Python matches and extends the Bash tooling (status table, locks,
  audit trail). |
  | Git safety gating | Maintenance modes block destructive operations on dirty working trees unless --allow-dirty is set (scripts/orchestrator.sh:181-199, scripts/lib/git_safety.sh:1-46). | Neither nh cleanup nor nh reprocess checks git status before deleting files (orchestrator/nh_cli/commands/cleanup.py, reprocess.py). | ❌ Feature missing from Python maintenance commands. |
  | Configuration management | Bash relies on exporting variables in config/env.sh (config/env.sh:1-60) with no CLI helpers. | nh config supports init/show/validate/get for .nh.toml plus env precedence handling (orchestrator/nh_cli/commands/config.py:1-210). | ➕ Python-only; adds a formal config system. |
  | Registry validation / migration | Bash reads static TSV files; no command to validate or migrate them. | nh registry validate/list/migrate provide TSV checks and SQLite migration utilities (orchestrator/nh_cli/commands/registry.py:1-190). | ➕ Python-only capability. |
  | Diagnostics | Bash has no built-in environment check. | nh diag inspects binaries, env vars, and directory permissions with JSON output if needed (orchestrator/nh_cli/commands/diag.py:1-120). | ➕ Python-only capability. |
  | Parity verification | Bash offers no automated comparison between Bash and Python outputs. | nh compare hashes each artifact (reports, tags, dashboards, exports) to confirm parity (orchestrator/nh_cli/commands/compare.py:1-200). | ➕ Python-only capability; critical for migration confidence. |
  | Telemetry / manifests | Bash writes flat log files but doesn’t generate manifests or hashes for idempotency. | Python creates structured manifests, completion markers, and JSONL ledger entries for every run (services/manifest.py, services/ledger.py, referenced in run.py:86-217). | ➕ Python-only enhancement, aiding retries and auditing. |

  Key takeaways

  - Core parity is close but not complete. Both ecosystems can run the daily prompts, clean artifacts, reprocess, publish, and install automation. However, Bash still owns Cloudflare retracts, git-safety guards, automated notifications, and the “force today” flow that kills an in-flight pipeline before rerunning.
  - Python brings significant net-new tooling. Configuration, registry management, diagnostics, structured telemetry, and the parity harness are all new capabilities that don’t exist in the Bash world.
  - Operational gaps remain before decommissioning Bash. If you need automatic notifications, cleanup-linked Cloudflare awareness, or an operator-friendly “nuke today and rerun” action, the Bash scripts are still required. Python equivalents would need git-safety hooks plus deeper integration with notifier/publish scripts to claim full feature parity.

---

## Full test plan for orchestrator

  1. Run Python CLI test suite
      - From repo root: ./tests/test_python_cli.sh.
      - Expect pytest to execute ~133 tests with coverage (integration + unit tests for git safety, Cloudflare, notifier, etc.) and exit 0.
  2. Exercise cleanup command
      - Dirty repo check: create a temp file (touch foo.tmp) and run cd orchestrator && poetry run nh cleanup --dry-run. Command should refuse to proceed and list dirty files.
      - Clean tree path: remove the temp file, rerun nh cleanup --dry-run. Confirm console output lists planned deletions, Cloudflare context, and JSON mode (--json) reports git_clean: true. Check logs/audit/*.jsonl for entries including cloudflare_deploy_id.
  3. Verify reprocess guard
      - Make another working-tree change, run nh reprocess 2025-01-01 --dry-run; expect an error citing dirty git state.
      - Remove changes and rerun to ensure it delegates to nh run (dry run) successfully.
  4. Notifier hooks
  5. Cloudflare context
      - Run nh cleanup --dry-run; ensure output logs “Latest deployment ID: …” and the audit log entry contains IDs.
  6. Docs/config sanity
      - Open orchestrator/README.md and .nh.toml to confirm [maintenance] and [notifier] sections match expectations.
      - Run nh config init in a temp directory to verify the new sections populate correctly.
