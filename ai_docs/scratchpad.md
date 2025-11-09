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

### answering clarifying questions for the cleanup spec

Hi
