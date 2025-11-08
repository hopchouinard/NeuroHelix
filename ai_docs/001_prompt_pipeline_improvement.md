# Prompt Pipeline Management & Monitoring Improvements

## Background
Daily NeuroHelix research reports are assembled from a growing catalog of autonomous prompts. The current orchestration executes prompts in a mostly flat sequence without strong guarantees around category ordering, visibility into runtime behavior, or reactive alerting when a step fails. As the number of prompts and stakeholders increases, we need deterministic stage sequencing, reliable logging, and lightweight operational safeguards so the editorial team can trust each daily drop.

## Goals
1. Provide auditable runtime telemetry (start/end timestamps, errors) in per-day log files.
2. Surface a human-readable execution summary (success/failure) inside the daily report itself.
3. Automatically notify the admin (`chouinpa@gmail.com`) whenever a prompt fails, without blocking the rest of the run.

## Logging & Telemetry
1. **Daily Log Files**
   - Log file path format: `logs/prompt_execution_YYYY-MM-DD.log` (ISO date in local timezone).
   - For each prompt, log a structured entry containing:
     - Prompt ID/name & category
     - Stage (Research/Analysis/Meta)
     - Start timestamp (ISO8601)
     - End timestamp (ISO8601)
     - Duration in seconds
     - Status (`success` / `failure`)
     - Error payload (stack trace or stderr) when failures occur
   - Logs should be appended to throughout the day; orchestrator ensures file creation when missing.
2. **Resilience**
   - Logging must be best-effort and never crash the orchestrator. Errors writing to disk are captured in-memory and surfaced in the daily summary.

## Daily Report Integration
1. **Summary Section**
   - Append a dedicated “Prompt Execution Summary” section at the end of each daily report that lists every prompt with status, timestamps, and pointers to relevant sections.
   - Failed prompts are annotated with the error headline and a link/anchor to the log file for details.
2. **Data Inputs for Late Stages**
   - Analysis stage summary references the Research sections it synthesized from.
   - Meta stage outputs must explicitly note where their summarized content lives (e.g., “Strategic Implications derived from Analysis › Market Outlook”).

## Failure Handling & Notifications
1. **Non-blocking Failures**
   - If a prompt fails, the orchestrator records the failure, continues with the remaining prompts in its current stage, and still advances to later stages once all prompts of the current stage complete (successfully or not).
2. **Email Alerts**
   - On any prompt failure, send an email to `chouinpa@gmail.com` containing:
     - Prompt name and category
     - Stage and timestamp of failure
     - Path to the log file plus the relevant error snippet
   - Email notifications should batch multiple failures in a single message if they occur within the same run, but send immediately after the first failure if batching is not yet implemented.
3. **Escalation Visibility**
   - The email body includes guidance on how to rerun or skip the failing prompt, leveraging orchestrator commands if available.

## Implementation Notes
1. **Output Passing**
   - Persist each prompt’s output to a canonical location (existing behavior). Provide a stage completion barrier that collects file paths and injects them into the next stage’s prompt context.
2. **Summary Builder**
   - Extend the report generator to consume the orchestrator’s runtime ledger (JSON or in-memory structure) and append the formatted summary before publication.
3. **Email Transport**
   - Reuse existing SMTP/SendGrid helper if present; otherwise define a minimal transporter module with retry/backoff to avoid silent alert failures.

## Acceptance Criteria
1. `logs/prompt_execution_YYYY-MM-DD.log` contains well-formed entries for each prompt with start/end timestamps and status.
2. The daily report ends with a Prompt Execution Summary table/list showing every prompt and its success/failure state.
3. If a prompt fails, the orchestrator still completes all other prompts, marks the failure in the summary, and an email reaches `chouinpa@gmail.com` with the logged error details.

## Open Questions
1. Do we need configurable retry counts per prompt/category, or is a single attempt sufficient for now?
2. What is the acceptable SLA for the failure notification email (immediate vs. batched summary at the end of the run)?
3. Should the daily report summary include execution durations, or is status-only sufficient for stakeholders?

## Open Question Answers
1. Single attempt sufficient for now.
2. Batched summary at the end of the run.
3. Daily report summary include execution durations.
