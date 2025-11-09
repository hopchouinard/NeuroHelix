# 🧠 NeuroHelix Publishing & Layout Enhancement

## Purpose

Define the functional and design intent for expanding NeuroHelix’s publishing system to include both synthesized and raw research content, presented through a modern website interface inspired by IDE layouts.
This document serves as the design brief for an AI coding assistant to plan and implement the new features.

⸻

## Core Objective

NeuroHelix currently generates a daily synthesized report published via Astro.
The next iteration must also:
 1. Publish all raw source material that is produced in the path : `data/outputs/daily/YYYY-MM-DD/` alongside the synthesized report.
 2. Present it within a cohesive, modern interface that resembles the clarity and spatial organization of an IDE, without imitating an IDE literally.

⸻

## Functional Requirements

### 1. Dual-Layer Publishing
 - Continue publishing the daily synthesized report as the primary public artifact.
 - Add a “Source View” accessible via a button at the top of the daily report.
 - “Source View” exposes all intermediate files:
 - Research prompts
 - Raw summaries
 - Cross-analysis results
 - Insight drafts
 - Publishing must remain idempotent—rebuilding or re-publishing a single day cannot modify other reports.

⸻

### 2. Directory-Style Navigation
 - Represent each day’s publication as if it were a repo:
 - Root: Synthesized report (README.md equivalent)
 - Subdirectories: Research, Summaries, Insights, etc.
 - Provide sidebar navigation reflecting this structure:
 - Collapsible folders
 - File icons
 - Hover highlights in electric violet
 - Each Markdown file should be renderable directly inside the site with full syntax highlighting.

⸻

### 3. Layout & Design Language
 - Overall tone once exploring the "Source View" of a daily report: modern website with IDE-inspired clarity.
 - Not a fake code editor—just echo the feel of one.
 - Color palette:
 - Background: Charcoal gray (identical to the existing NeuroHelix site)
 - Accent: Electric violet (identical to the existing NeuroHelix site)
 - Typography: identical to the existing NeuroHelix site.
 - Layout structure:
 - Persistent hero toolbar (top banner) for navigation, title, and context actions with a background image.
 - Sidebar panel resembling an IDE’s file explorer.
 - Main reading pane centered with proportional margins and line-length control.
 - Command-palette-style global search (leveraging existing NeuroHelix components).
 - Toggle buttons for “Processed View" (Rendered markdown) / “Source View” (Raw files).
 - Table of Contents outline view for each page.

⸻

### 4. Raw Data Rendering
 - Routes:/Daily/YYYY-MM-DD/source/<filename>
 - Each raw document view must include:
 - Breadcrumb path back to the synthesized report.
 - File metadata (timestamp, file path, originating prompt).
 - Automatic code/JSON highlighting if detected inside Markdown.
 - Keep content-presentation separation: data stays Markdown/JSON, rendering via Astro components.

⸻

### 5. Implementation Notes
 - Build system: extend existing Bash → Astro pipeline; no dependency overhaul.
 - Store new view templates under src/pages/source or equivalent.
 - Introduce new design tokens for IDE highlights and electric-violet accents.
 - Maintain responsive design and accessibility (WCAG 2.1 AA or better).
 - Support selective rebuilds: --day <YYYY-MM-DD> flag to regenerate a single day.
⸻

### 6. Other Enhancements
 - Add a meta-index page that lists all published days like a repo file tree.
 - Enable light/dark theme toggle for accessibility.
 - Allow JSON metadata export for future vector-database ingestion.

⸻

End of specification.
