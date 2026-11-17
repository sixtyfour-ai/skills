# Workflows API Reference

Workflows chain blocks into automated pipelines that process thousands of records: search → enrich → filter → export.

## When to use workflows

- **Single record** → use sync endpoints directly (no workflow needed)
- **Just need a list of names/titles/companies** → deep search or filter search (no workflow needed)
- **Need enrichment, emails, phones, or custom fields on 10+ records** → build a workflow

## Type safety

Every block operates on either **LEAD** (people) or **COMPANY** data. Mismatched types cause failures.

**LEAD-only blocks**: `find_email`, `find_phone`, `lead_enrichment`, `verify_email`, `reverse_email`, `reverse_phone`

**COMPANY-only blocks**: `company_enrichment`

**Universal blocks**: `filter`, `deduplicate`, `deduplicate_wrt_notebook`, `append_to_notebook`, `remove_columns`, `group_by`, `llm_openai`, `transform_data`, `outgoing_webhook`, `send_slack_message`

**Type conversion**:
- COMPANY → LEAD: use `company_to_leads` block
- LEAD → COMPANY: use `leads_to_company` block

Common mistake:
- `company_enrichment` → `find_email` — **FAILS** (type mismatch)
- `company_enrichment` → `company_to_leads` → `find_email` — **CORRECT**


## Creating a workflow

### POST /v1/workflows

```bash
API_URL="${SIXTYFOUR_API_ENDPOINT:-https://api.sixtyfour.ai}"

curl -X POST "$API_URL/v1/workflows" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Lead Enrichment",
    "description": "Enrich leads with emails and company data",
    "definition": {
      "blocks": [
        {"sequence_number": 1, "block_name": "webhook", "block_type": "webhook", "block_id": "input", "specs": {}},
        {"sequence_number": 2, "block_name": "find_email", "block_type": "find_email", "block_id": "emails", "specs": {"mode": "PROFESSIONAL"}},
        {"sequence_number": 3, "block_name": "append_to_notebook", "block_type": "append_to_notebook", "block_id": "save", "specs": {"notebook_id": "__create_new__", "notebook_name": "Results"}}
      ],
      "edges": [
        {"from_block_id": "input", "to_block_id": "emails"},
        {"from_block_id": "emails", "to_block_id": "save"}
      ]
    }
  }'
```

The response includes the `workflow_id`. Workflows you pass rows to **must** start with a `webhook` block.

### Running a workflow

```bash
curl -X POST "$API_URL/v1/workflows/WORKFLOW_ID/runs" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"input": [
    {"full_name": "Jane Doe", "company": "Acme Corp"},
    {"full_name": "John Smith", "company": "Globex Inc"}
  ]}'
```

Returns a Job: `{"job_id": "job_...", "status": "queued", "operation": "workflows.run", ...}`

- `input` — rows to run on, for workflows that start with a `webhook` block.
- `source_overrides` — settings to change on the first block for this run only. For a Read CSV source, upload the file to `POST /v1/files` and pass `{"resource_handle_id": "FILE_ID"}`.
- `result_formats` — file formats to save, such as `["csv", "ndjson"]`. Default: `csv`.
- Send an `Idempotency-Key` header so a retried start does not run twice.

### Polling and downloading

```bash
python3 scripts/poll_job.py JOB_ID --timeout 1800 --output /tmp/results.csv
```

Or manually:

```bash
curl "$API_URL/v1/jobs/JOB_ID" -H "x-api-key: $SIXTYFOUR_API_KEY"
```

When `status` is `succeeded`, `result` lists the output files, each with a signed `download_url` (valid 15 minutes; read the Job again to refresh):

```json
"result": [
  {"filename": "results.csv", "content_type": "text/csv", "row_count": 2, "block_number": 3, "download_url": "https://api.sixtyfour.ai/storage/download/...", "download_expires_in_seconds": 900}
]
```

A `succeeded` run can include failed rows. A `failed` or `canceled` Job has no `result`.


## Block reference

### Discover all blocks

```bash
curl "$API_URL/v1/workflows/blocks" -H "x-api-key: $SIXTYFOUR_API_KEY"
```

Returns all block types with their specs schemas.

### Input blocks

**webhook** — for API-triggered workflows:
```json
{"block_type": "webhook", "specs": {}}
```

**read_csv** — read rows from an uploaded file:
```json
{"block_type": "read_csv", "specs": {"dataframe_type": "LEAD"}}
```
- `dataframe_type`: `"LEAD"` or `"COMPANY"`
- Upload the file to `POST /v1/files` and pass its `file_id` as `source_overrides.resource_handle_id` when you start the run
- To start from a search, run the search first (`POST /v1/people/search` or `/v1/companies/search`), download its CSV and upload that file. A workflow created through the API does not run a search itself.

### Enrichment blocks

**lead_enrichment** — enrich people with custom fields:
```json
{"block_type": "lead_enrichment", "specs": {
  "return_fields": {
    "current_salary_estimate": {"description": "Estimated current salary range", "type": "str"},
    "years_experience": {"description": "Total years of experience", "type": "int"},
    "skills": {"description": "Key technical skills", "type": "list[str]"},
    "is_hiring_manager": {"description": "Whether this person is a hiring manager", "type": "bool"}
  }
}}
```

Supported types: `"str"`, `"int"`, `"float"`, `"bool"`, `"list[str]"`, `"list[int]"`, `"dict"`

**company_enrichment** — enrich companies:
```json
{"block_type": "company_enrichment", "specs": {
  "return_fields": {
    "annual_revenue": {"description": "Estimated annual revenue in USD", "type": "str"},
    "employee_count": {"description": "Total employees", "type": "int"}
  },
  "find_people": true,
  "people_focus_prompt": "C-suite and VP-level"
}}
```

**find_email**: `{"specs": {"mode": "PROFESSIONAL"}}`

**find_phone**: `{"specs": {}}`

### Data operation blocks

**filter**:
```json
{"block_type": "filter", "specs": {
  "filters": [
    {"column": "email_status", "operator": "equals", "value": "OK"},
    {"column": "employee_count", "operator": "greater", "value": 100, "logic": "and"}
  ]
}}
```
Operators: `equals`, `not_equals`, `contains`, `not_contains`, `greater`, `less`, `in`, `not_in`, `is_empty`, `is_not_empty`, `matches` (regex)

**deduplicate**: `{"specs": {}}`

**remove_columns**: specify columns to drop

**group_by**: group rows by a column

### Output blocks

**append_to_notebook**: `{"specs": {"notebook_id": "__create_new__", "notebook_name": "Results"}}`

**send_slack_message**: send results to a Slack channel

**outgoing_webhook**: POST results to a URL

### Discovery blocks

**company_to_leads**: convert COMPANY rows to LEAD rows (extracts people)

**leads_to_company**: convert LEAD rows to COMPANY rows

**google_maps_search**: search Google Maps for businesses

### All available block categories

- **Input**: webhook, read_csv, read_notebook
- **Enrichment**: company_enrichment, lead_enrichment, find_email, find_phone, verify_email, reverse_email, reverse_phone
- **Discovery**: company_to_leads, leads_to_company, github_find_people, google_maps_search
- **Web**: scrape_web, backlinks_referring_domains, find_subdomains
- **Social**: x_search, tiktok_get_following, kaggle_leaderboard
- **AI**: llm_openai, qa_agent, research_agent, transform_data
- **Data ops**: filter, deduplicate, deduplicate_wrt_notebook, group_by, remove_columns
- **Output**: append_to_notebook, send_slack_message, outgoing_webhook
- **Integrations**: hubspot_import
- **Specialty**: yc_batches, yc_companies


## Workflow management

```bash
# List workflows (page_size, cursor -> items, next_cursor)
curl "$API_URL/v1/workflows" -H "x-api-key: $SIXTYFOUR_API_KEY"

# Get workflow details
curl "$API_URL/v1/workflows/WORKFLOW_ID" -H "x-api-key: $SIXTYFOUR_API_KEY"

# Update a workflow (send only what changes)
curl -X PATCH "$API_URL/v1/workflows/WORKFLOW_ID" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated Name"}'

# Delete a workflow
curl -X DELETE "$API_URL/v1/workflows/WORKFLOW_ID" -H "x-api-key: $SIXTYFOUR_API_KEY"

# List a workflow's runs
curl "$API_URL/v1/jobs?workflow_id=WORKFLOW_ID" -H "x-api-key: $SIXTYFOUR_API_KEY"

# Cancel a running workflow
curl -X POST "$API_URL/v1/jobs/JOB_ID/cancel" -H "x-api-key: $SIXTYFOUR_API_KEY"
```


## Scheduling workflows

Trigger a workflow on a recurring cadence without polling or external cron infrastructure. A schedule binds a `workflow_id` to a `cron_expression` and `timezone`. The workflow must already exist and (to receive rows) start with a `webhook` block.

A schedule is bound to the creating user or API key — if that entity loses access to the org, the schedule is automatically paused and `disabled_reason` is set on the response. Scheduled runs are billed the same as manual runs.

### POST /v1/schedules (create)

```bash
curl -X POST "$API_URL/v1/schedules" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "WORKFLOW_ID",
    "name": "Daily lead refresh",
    "cron_expression": "0 9 * * *",
    "timezone": "America/New_York",
    "description": "Re-enrich the prospect list every morning"
  }'
```

| Field | Required | Description |
|-------|----------|-------------|
| workflow_id | yes | The workflow to run — must already exist |
| name | yes | Up to 120 characters |
| cron_expression | yes | Standard 5-field cron (`minute hour day month weekday`) |
| timezone | no | IANA timezone, e.g. `America/Los_Angeles`. Defaults to `UTC` |
| description | no | Free-form text |
| is_active | no | Defaults to `true`. Set `false` to save without activating |

**Response**: `schedule_id`, `workflow_id`, `name`, `description`, `cron_expression`, `timezone`, `is_active`, `disabled_reason`, `next_run_times` (array of upcoming ISO timestamps), `created_at`, `updated_at`.

### GET /v1/schedules (list)

```bash
curl "$API_URL/v1/schedules" -H "x-api-key: $SIXTYFOUR_API_KEY"
# Returns items and next_cursor. Optional: filter to one workflow
curl "$API_URL/v1/schedules?workflow_id=WORKFLOW_ID" -H "x-api-key: $SIXTYFOUR_API_KEY"
```

### GET /v1/schedules/{schedule_id} (get one)

```bash
curl "$API_URL/v1/schedules/SCHEDULE_ID" -H "x-api-key: $SIXTYFOUR_API_KEY"
```

### PATCH /v1/schedules/{schedule_id} (update)

All fields optional — only send what changes. Reactivating a paused/auto-disabled schedule re-binds it to the caller and clears `disabled_reason`.

```bash
curl -X PATCH "$API_URL/v1/schedules/SCHEDULE_ID" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'
```

### DELETE /v1/schedules/{schedule_id} (delete)

```bash
curl -X DELETE "$API_URL/v1/schedules/SCHEDULE_ID" -H "x-api-key: $SIXTYFOUR_API_KEY"
```

Deleting a schedule does not affect the underlying workflow or its run history.


## Tips

- Add `filter` blocks BEFORE enrichment to reduce credit usage (enrich only the rows you need)
- Use `deduplicate` to remove duplicates before enrichment
- One enrichment block with multiple `return_fields` is better than multiple enrichment blocks
- Workflows with `read_csv` blocks take their rows from the file in `source_overrides.resource_handle_id` on each run
- Workflows with `webhook` blocks take their rows from `input` on each run
- Use `GET /v1/workflows/blocks` to discover all available blocks and their specs schemas
