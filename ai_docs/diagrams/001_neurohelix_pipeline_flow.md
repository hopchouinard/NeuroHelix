# NeuroHelix Pipeline Flow

## Overview
This diagram illustrates the complete NeuroHelix automated research and ideation pipeline, showing how it processes daily research cycles from prompt execution through dashboard generation and optional notifications.

## Diagram

```mermaid
flowchart TD
    %% High contrast styling for readability
    classDef config fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
    classDef execution fill:#9C27B0,stroke:#7B1FA2,stroke-width:2px,color:#fff
    classDef aggregation fill:#4CAF50,stroke:#388E3C,stroke-width:2px,color:#fff
    classDef visualization fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#fff
    classDef notification fill:#E91E63,stroke:#C2185B,stroke-width:2px,color:#fff
    classDef data fill:#8BC34A,stroke:#689F38,stroke-width:2px,color:#fff

    subgraph cfg [Configuration]
        direction LR
        conf["/config/env.sh"]:::config
        tsv["/config/searches.tsv"]:::config
    end

    subgraph trigger [Automation Trigger]
        launchd["launchd Job<br>(7:00 AM Daily)"]:::execution
        manual["Manual Execution<br>./scripts/orchestrator.sh"]:::execution
    end
    
    subgraph exec [Step 1: Execution]
        direction TB
        run["run_prompts.sh"]:::execution
        parallel["Parallel Execution<br>(MAX_PARALLEL_JOBS)"]:::execution
        prompts["Research Prompts"]:::data
    end

    subgraph agg [Step 2: Aggregation]
        direction TB
        aggregate["aggregate_daily.sh"]:::aggregation
        synthesis["AI Synthesis<br>(Gemini CLI)"]:::aggregation
        report["Daily Report"]:::data
    end

    subgraph viz [Step 3: Visualization]
        direction TB
        dashboard["generate_dashboard.sh"]:::visualization
        html["Interactive HTML<br>Dashboard"]:::data
    end

    subgraph notif [Step 4: Notification]
        direction TB
        notify["notify.sh<br>(Optional)"]:::notification
    end

    %% Data Storage
    subgraph data [Data Directory]
        direction TB
        outputs["data/outputs/daily/<br>YYYY-MM-DD/*.md"]:::data
        complete[".execution_complete"]:::data
        reports["data/reports/<br>daily_report_*.md"]:::data
        dash["dashboards/<br>dashboard_*.html"]:::data
    end

    %% Flow Connections
    launchd --> run
    manual --> run
    conf --> run
    tsv --> prompts
    prompts --> parallel
    parallel --> outputs
    parallel --> complete

    outputs --> aggregate
    synthesis --> report
    aggregate --> report
    report --> dashboard
    dashboard --> html
    dashboard --> dash
    
    complete -.-> notify
    html -.-> notify
    
    %% Add labels
    click launchd "Daily automated execution at 7 AM"
    click manual "Can be run on-demand"
    click run "Executes research prompts"
    click parallel "Processes multiple prompts simultaneously"
    click aggregate "Combines daily findings"
    click synthesis "AI-powered analysis"
    click dashboard "Generates interactive view"
    click notify "Sends completion notification"
```

## Key Components

### Configuration
- `config/env.sh`: Environment variables, settings, and paths
- `config/searches.tsv`: Research prompts with domains, priorities, and enabled status

### Execution Layer
- `scripts/executors/run_prompts.sh`: Main prompt execution engine
- Parallel execution of enabled prompts from searches.tsv
- Outputs stored as Markdown files by date

### Aggregation Layer
- `scripts/aggregators/aggregate_daily.sh`: Results synthesizer
- Combines all domain outputs into unified report
- AI-powered cross-domain analysis using Gemini CLI

### Visualization Layer
- `scripts/renderers/generate_dashboard.sh`: Dashboard generator
- Creates interactive HTML dashboard
- Links to latest version for easy access

### Notification Layer (Optional)
- `scripts/notifiers/notify.sh`: Optional notifications
- Can be configured for email or Discord
- Disabled by default (ENABLE_NOTIFICATIONS=false)

## Related Files
- `/scripts/orchestrator.sh`: Main pipeline coordinator
- `/launchd/com.neurohelix.daily.plist`: Automation configuration
- `/config/env.sh`: Environment and settings
- `/config/searches.tsv`: Research prompt definitions
- `/scripts/executors/run_prompts.sh`: Prompt execution engine
- `/scripts/aggregators/aggregate_daily.sh`: Results synthesizer
- `/scripts/renderers/generate_dashboard.sh`: Dashboard generator
- `/scripts/notifiers/notify.sh`: Notification sender
