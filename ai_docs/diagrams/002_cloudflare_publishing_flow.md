# CloudFlare Pages Publishing Flow

## Overview
This diagram illustrates the complete publishing pipeline for the NeuroHelix static site to CloudFlare Pages. It shows how daily reports are transformed into JSON payloads, ingested into Astro content collections, built into a static site, and deployed to CloudFlare's edge network.

## Diagram

```mermaid
flowchart TD
    %% High contrast styling for readability
    classDef source fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
    classDef transform fill:#9C27B0,stroke:#7B1FA2,stroke-width:2px,color:#fff
    classDef build fill:#4CAF50,stroke:#388E3C,stroke-width:2px,color:#fff
    classDef deploy fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#fff
    classDef output fill:#E91E63,stroke:#C2185B,stroke-width:2px,color:#fff
    classDef data fill:#8BC34A,stroke:#689F38,stroke-width:2px,color:#fff

    subgraph source [Data Source]
        direction TB
        report["Daily Report<br>daily_report_YYYY-MM-DD.md"]:::source
        tags["Tag Generator Output<br>keyword_tag_generator.md"]:::source
    end

    subgraph export [Phase 1: Export Payload]
        direction TB
        exporter["export_site_payload.sh"]:::transform
        parser["Markdown Parser<br>(awk/grep/sed)"]:::transform
        validator["JSON Validator<br>(jq)"]:::transform
        payload["Publishing Payload<br>YYYY-MM-DD.json"]:::data
    end

    subgraph prebuild [Phase 2: Prebuild Scripts]
        direction TB
        ingest["ingest.mjs"]:::transform
        searchbuild["build-search-index.mjs"]:::transform
        
        subgraph ingestProcess [Ingest Process]
            direction LR
            convert["JSON → Markdown"]:::transform
            frontmatter["Add YAML Frontmatter"]:::transform
            validate["Zod Schema Validation"]:::transform
        end
        
        subgraph searchProcess [Search Index]
            direction LR
            minisearch["MiniSearch Engine"]:::transform
            compress["Gzip Compression<br>(if >2MB)"]:::transform
        end
    end

    subgraph astrobuild [Phase 3: Astro Build]
        direction TB
        collections["Content Collections<br>(Type-Safe Data)"]:::build
        ssg["Static Site Generation"]:::build
        routing["Dynamic Routes<br>/dashboards/[date]"]:::build
        tailwind["Tailwind CSS Processing"]:::build
    end

    subgraph deployment [Phase 4: CloudFlare Deploy]
        direction TB
        wrangler["Wrangler CLI<br>pages deploy"]:::deploy
        upload["Upload to CloudFlare"]:::deploy
        edge["Edge Network Distribution"]:::deploy
    end

    subgraph outputs [Generated Outputs]
        direction TB
        content["src/content/dashboards/<br>*.md"]:::data
        tagsjson["src/data/tags.json"]:::data
        searchindex["public/search-index.json"]:::data
        dist["dist/<br>(Static Site)"]:::data
        site["Production Site<br>neurohelix.patchoutech.com"]:::output
    end

    %% Flow Connections - Phase 1
    report --> exporter
    tags --> exporter
    exporter --> parser
    parser --> validator
    validator --> payload
    payload --> outputs

    %% Flow Connections - Phase 2
    payload --> ingest
    payload --> searchbuild
    ingest --> convert
    convert --> frontmatter
    frontmatter --> validate
    validate --> content
    ingest --> tagsjson
    
    searchbuild --> minisearch
    minisearch --> compress
    compress --> searchindex

    %% Flow Connections - Phase 3
    content --> collections
    tagsjson --> collections
    searchindex --> collections
    collections --> ssg
    ssg --> routing
    routing --> tailwind
    tailwind --> dist

    %% Flow Connections - Phase 4
    dist --> wrangler
    wrangler --> upload
    upload --> edge
    edge --> site

    %% Idempotency checks
    payload -.->|"Idempotency Check"| exporter
    content -.->|"Skip if exists"| ingest
    searchindex -.->|"Rebuild on change"| searchbuild
```

## Key Components

### Phase 1: Export Payload
- **export_site_payload.sh**: Parses daily markdown reports into structured JSON
- Extracts metadata, sections, tags, recommendations, and strategic implications
- Validates JSON output with jq
- Implements idempotency checks to avoid re-processing unchanged reports
- Output: `data/publishing/YYYY-MM-DD.json`

### Phase 2: Prebuild Scripts
- **ingest.mjs**: Converts JSON payloads to Astro content collection format
  - Creates markdown files with YAML frontmatter
  - Validates against Zod schema
  - Aggregates all tags into centralized tags.json
  - Output: `src/content/dashboards/*.md` and `src/data/tags.json`

- **build-search-index.mjs**: Generates client-side search index
  - Uses MiniSearch library for fast client-side search
  - Indexes: date, title, summary, tags, full_text
  - Auto-compresses if index exceeds 2MB
  - Output: `public/search-index.json` (and .gz variant)

### Phase 3: Astro Build
- **Content Collections**: Type-safe data layer with Zod validation
- **Static Site Generation**: Pre-renders all pages at build time
- **Dynamic Routing**: Creates `/dashboards/[date]/` routes
- **Tailwind CSS v4**: Modern utility-first styling
- Output: `dist/` directory with fully static site

### Phase 4: CloudFlare Deployment
- **static_site.sh**: Orchestrates the complete build and deploy process
- **Wrangler CLI**: CloudFlare's official deployment tool
- **Configuration**:
  - Project: `neurohelix-site`
  - Branch: `production`
  - Domain: `neurohelix.patchoutech.com`
- Includes deployment verification and summary JSON generation

## Related Files
- `/scripts/renderers/export_site_payload.sh`: JSON payload exporter
- `/scripts/publish/static_site.sh`: CloudFlare deployment orchestrator
- `/site/package.json`: Build configuration and scripts
- `/site/astro.config.mjs`: Astro framework configuration
- `/site/scripts/ingest.mjs`: Content ingestion script
- `/site/scripts/build-search-index.mjs`: Search index builder
- `/site/src/content/config.ts`: Content collection schema
- `/site/src/pages/index.astro`: Dashboard listing page
- `/site/src/pages/dashboards/[date].astro`: Individual dashboard page
- `/config/env.sh`: CloudFlare project configuration
