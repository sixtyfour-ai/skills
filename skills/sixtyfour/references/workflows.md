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

### POST /workflows/create_workflow

```bash
API_URL="${SIXTYFOUR_API_ENDPOINT:-https://api.sixtyfour.ai}"

curl -X POST "$API_URL/workflows/create_workflow" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_name": "Lead Enrichment",
    "workflow_description": "Enrich leads with emails and company data",
    "workflow_definition": {
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

API-triggered workflows **must** start with a `webhook` block.

### Running a workflow

```bash
curl -X POST "$API_URL/workflows/run?workflow_id=WF_ID" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"webhook_payload": [
    {"full_name": "Jane Doe", "company": "Acme Corp"},
    {"full_name": "John Smith", "company": "Globex Inc"}
  ]}'
```

Returns: `{"job_id": "run_xyz", "status": "queued"}`

### Polling and downloading

```bash
python3 scripts/poll_job.py workflow run_xyz --timeout 1800 --output /tmp/results.csv
```

Or manually:

```bash
# Poll status
curl "$API_URL/workflows/runs/run_xyz/live_status" -H "x-api-key: $SIXTYFOUR_API_KEY"

# Download results (after completion)
curl "$API_URL/workflows/runs/run_xyz/results/download-links" -H "x-api-key: $SIXTYFOUR_API_KEY"
```


## Block reference

### Discover all blocks

```bash
curl "$API_URL/workflows/blocks" -H "x-api-key: $SIXTYFOUR_API_KEY"
```

Returns all block types with their specs schemas.

### Input blocks

**webhook** — for API-triggered workflows:
```json
{"block_type": "webhook", "specs": {}}
```

**search** — run a search as the first step:
```json
{"block_type": "search", "specs": {
  "query": "Software Engineers at Google in San Francisco",
  "dataframe_type": "LEAD",
  "max_results": 500,
  "auto_execute": true
}}
```
- `dataframe_type`: `"LEAD"` or `"COMPANY"`
- `auto_execute: true` runs the search at workflow creation time
- Use specific company/role names, not vague categories

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

- **Input**: webhook, read_notebook, search
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
# List all workflows
curl "$API_URL/workflows" -H "x-api-key: $SIXTYFOUR_API_KEY"

# Get workflow details
curl "$API_URL/workflows/WF_ID" -H "x-api-key: $SIXTYFOUR_API_KEY"

# Update a workflow (upsert)
curl -X POST "$API_URL/workflows/update_workflow?workflow_id=WF_ID" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"workflow_name": "Updated Name"}'

# Delete a workflow
curl -X POST "$API_URL/workflows/delete_workflow?workflow_id=WF_ID" \
  -H "x-api-key: $SIXTYFOUR_API_KEY"

# Cancel a running workflow
curl -X POST "$API_URL/workflows/cancel?job_id=RUN_ID" \
  -H "x-api-key: $SIXTYFOUR_API_KEY"
```


## Tips

- Add `filter` blocks BEFORE enrichment to reduce credit usage (enrich only the rows you need)
- Use `deduplicate` to remove duplicates before enrichment
- One enrichment block with multiple `return_fields` is better than multiple enrichment blocks
- `search` queries should use specific company/role names, not vague categories
- Workflows with `search` blocks use `auto_execute: true` to run the search at creation time
- Workflows with `webhook` blocks are for API-triggered batch processing
- Use `GET /workflows/blocks` to discover all available blocks and their specs schemas
