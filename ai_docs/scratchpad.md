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
