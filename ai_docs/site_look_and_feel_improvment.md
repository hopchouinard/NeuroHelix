# Site Look & Feel Improvement Specification

## Background
The upcoming Astro-powered NeuroHelix site will become the canonical destination for daily AI research dashboards. To maximize engagement and discoverability, the initial UI pass must deliver a cohesive visual language, deep navigation affordances, and intuitive content discovery patterns. This spec covers the first wave of experience enhancements centered on rendering Markdown reports beautifully, exposing tags and categories, and providing multiple discovery paths.

## Goals
1. Present Markdown reports with a polished, GitHub-quality typographic system (Fira Code + modern sans pairings) that preserves hierarchy and readability.
2. Surface report metadata (tags, categories, dates) prominently through a hero, tag cloud, filters, and search—driving faster access to relevant insights.
3. Reinforce brand identity via a hero section with imagery, mission statement, and consistent spacing/alignment rules.
4. Add footer content for trust (copyright + contact/social links).
5. Keep implementation client-side only (no auth/APIs) while maintaining performance and accessibility.

## Functional Requirements
1. **Hero Section**
   - Full-width banner at top of dashboard home page.
   - Background image (local asset stored under `site/src/assets/hero.jpg` or external CDN) with overlay gradient (#1a1a1a → rgba(26,26,26,0.6)).
   - Content: NeuroHelix logo/wordmark (placeholder), mission blurb (<160 characters), CTA button linking to latest report, and metadata (e.g., days published, total insights).
   - Responsive layout: stacked on mobile, two-column on >=1024px.

2. **Markdown Rendering Enhancements**
   - Apply consistent styles to headings (h1-h6), paragraphs, lists, blockquotes, code (inline & blocks), tables, footnotes.
   - Use `Fira Code` for headings and code, `Inter` or system sans for body text.
   - Mirror GitHub markdown spacing (24px between sections, 16px for paragraphs, 32px before h2).
   - Add syntax highlighting for code blocks via Shiki/Prism; fallback colors defined in CSS variables.
   - Ensure anchor links for headings (Astro `markdownHeadingId` feature) for deep linking.

3. **Tag Cloud**
   - Display all unique tags across currently ingested reports.
   - Visual weight scaled by tag frequency (min font-size 0.875rem, max 1.5rem).
   - Clicking a tag filters visible reports and highlights active state.
   - Provide “Clear filters” control when any tag filter is active.

4. **Category Filters**
   - Buttons or pills representing curated categories (e.g., AI Trends, Market Analysis, Regulation, Strategy, Tooling).
   - Support multi-select with toggle pills; update report grid/list as filters change.
   - Category metadata sourced from report payload (explicit field) or mapped from tags.

5. **Search Functionality**
   - Client-side search input with debounced (200ms) query.
   - Search scope: report title, executive summary, sections, tags.
   - Results update in-place (no navigation) with match count + highlight snippet.
   - No dependency on external APIs; reuse JSON index emitted during build.

6. **Report List/Grid**
   - Card layout showing date, title, key themes, tags, excerpt, “View report” CTA.
   - Should respect active filters/search; show empty state message with reset action.
   - Provide sort dropdown (Newest → Oldest by default).

7. **Footer**
   - Persistent footer with © NeuroHelix {current year}, contact email link, and icons linking to Twitter/X, LinkedIn, GitHub (insert actual URLs once available).
   - Background #111, text #d1d5db; ensure sufficient contrast.

8. **Spacing & Alignment System**
   - Establish 4px spacing scale (4/8/12/16/24/32/48 px) and apply consistently across hero, cards, filters, tag cloud, footer.
   - Use CSS grid/stack utilities for alignment; define container max-width 1200px.

9. **Criticality**
   - Feature flagged as “must ship” for MVP launch; orchestrator pipeline should fail if Sass/CSS build errors occur.

## Non-Functional Requirements
- **Performance**: Tag cloud/search/filter interactions under 100ms on mid-tier laptops; avoid re-rendering entire page (use derived state).
- **Accessibility**: Keyboard focus states for search, tags, category pills; aria-live region for result count; color contrast ≥ WCAG AA.
- **Responsiveness**: Layout must support breakpoints (≤640px single column, 641-1023px two-column hero, ≥1024px full layout).
- **Maintainability**: Encapsulate styles via CSS modules, Tailwind, or scoped styles to prevent global bleed; document tokens in `site/src/styles/tokens.css`.

## Data Dependencies
- Report metadata (title, date, slug, summary, tags, categories) from `data/publishing/*.json`.
- Search index JSON generated at build time (MiniSearch/Fuse friendly structure).
- Tag frequency computed during build step or on client from dataset; prefer pre-computed counts in data payload.

## UX & Component Specifications
1. **HeroSection** component
   - Props: `headline`, `subcopy`, `ctaLabel`, `ctaHref`, `stats` array.
   - Background overlay gradient + parallax effect optional.

2. **TagCloud** component
   - Inputs: `tags: Array<{ name: string; count: number; selected: boolean }>`.
   - Weighted styling via CSS custom property `--tag-weight`.

3. **CategoryFilters** component
   - Pill buttons with icon + label; active state uses `#8b5cf6` fill.

4. **SearchBar** component
   - Input + icon; show placeholder “Search dashboards…”; include keyboard shortcut hint (`/`).

5. **ReportCard** component
   - Structured content with tag chips, categories, summary snippet, CTA.

6. **MarkdownRenderer**
   - Wrap Astro Markdown component with bespoke stylesheet; include table overflow handling, callout blocks.

7. **Footer**
   - Layout with left-aligned copyright, right-aligned social icons.

## CSS/Tokens
Define tokens in `tokens.css`:
```
:root {
  --color-bg-primary: #1a1a1a;
  --color-bg-surface: #111827;
  --color-accent: #8b5cf6;
  --color-text-primary: #e5e7eb;
  --color-text-muted: #94a3b8;
  --font-heading: 'Fira Code', 'Fira Mono', monospace;
  --font-body: 'Inter', 'SF Pro', system-ui;
  --radius-lg: 24px;
  --radius-md: 16px;
  --radius-sm: 8px;
}
```
Include GitHub-esque markdown defaults (borders, table striping, blockquote bar) and ensure code blocks have distinct background (#0f172a) and horizontal scroll.

## Analytics & Telemetry
- Add Cloudflare Web Analytics script to layout; track hero CTA clicks, filter usage, search queries (no PII) via custom data-* attributes and Cloudflare Workers analytics if needed.

## Risks & Mitigations
- **Performance**: Large datasets may slow tag cloud; precompute counts and lazy-render cards.
- **Font Loading**: Host Fira Code locally or use Fontsource; ensure `font-display: swap`.
- **Image Assets**: Hero background must be optimized (≤300KB) and have dark overlay for text legibility.

## Task Breakdown
| # | Task | Owner | Notes |
|---|------|-------|-------|
|1|Define typography/spacing tokens in `tokens.css`|Design/Frontend|Include documentation comments|
|2|Implement MarkdownRenderer with GitHub-style CSS + syntax highlighting|Frontend|Use Shiki or Prism plugin|
|3|Create HeroSection component + responsive styling|Frontend|Add placeholder imagery|
|4|Build TagCloud component with weighted styles + filter wiring|Frontend|Needs keyboard support|
|5|Implement CategoryFilters component + multi-select logic|Frontend|Sync with dataset categories|
|6|Add SearchBar + client-side search integration (debounced)|Frontend|Uses existing JSON index|
|7|Create ReportCard grid with empty/loading states|Frontend|A11y messaging|
|8|Add Footer component with social/contact links|Frontend|Use SVG icons|
|9|Wire global state management (e.g., minimal store or signals) for search/filter/tag interactions|Frontend|Ensure derived counts update|
|10|QA responsiveness, accessibility, and Lighthouse >90|QA|Document scenarios|

## Open Questions
1. Are there brand assets (logo, hero imagery) available, or should we design placeholders?
2. Should hero CTA point to the latest report or a curated “Start here” guide?
3. Are category mappings fixed or should they be inferred dynamically from tags/metadata?
4. Any restrictions on which social/contact links appear in the footer?

This spec ensures the NeuroHelix dashboard experience is visually compelling, discoverable, and consistent with modern documentation styling while remaining achievable within the Astro static-site stack.
