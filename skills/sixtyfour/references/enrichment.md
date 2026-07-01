# Enrichment API Reference

## People Intelligence

Enrich a person with any data you define. The `struct` field is fully flexible — describe any fields and the AI research agent will find them.

### POST /people-intelligence (sync)

```bash
API_URL="${SIXTYFOUR_API_ENDPOINT:-https://api.sixtyfour.ai}"

curl -X POST "$API_URL/people-intelligence" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "lead_info": {
      "full_name": "Jane Doe",
      "company": "Acme Corp",
      "linkedin_url": "https://linkedin.com/in/janedoe"
    },
    "struct": {
      "email": "Professional email address",
      "phone": "Direct phone number",
      "title": "Current job title",
      "years_experience": "Total years of professional experience",
      "skills": "Key technical skills"
    },
    "tier": "low"
  }'
```

**lead_info** — provide as many identifiers as possible for better matching:
- `full_name`, `first_name`, `last_name`
- `company`, `company_domain`
- `linkedin_url`, `email`

**struct** — dict of `field_name: description`. The description guides the AI agent — be specific about what you want. There is no fixed schema; define any fields that make sense for your use case.

**tier** — controls research depth:
- `micro`: Fastest, cheapest — single structured source lookup. Use for simple fields on well-indexed subjects. Lower coverage than `low`.
- `low` (default): Fast single-pass across well-indexed public sources. Good for standard fields (email, title, LinkedIn) with clear online presence.
- `medium`: Multi-source deep research with cross-referencing. Use when `low` comes back incomplete, subject is hard to find, or task needs higher confidence.
- `high`: Exhaustive OSINT-grade investigation — no time limit. Use for AML, KYC/KYB, fraud, due diligence. Requires enterprise access — if 403, direct user to https://cal.com/team/sixtyfour/discovery

**research_plan** (optional): A string guiding the research strategy (e.g. "Focus on public filings and press mentions").

**Response:**
```json
{
  "structured_data": {"email": "jane@acme.com", "title": "VP Engineering", ...},
  "notes": "Research notes with source details...",
  "references": {"https://linkedin.com/in/janedoe": "LinkedIn profile"},
  "confidence_score": 8.5
}
```

### POST /people-intelligence-async

Same parameters. Returns immediately with a job ID:
```json
{"task_id": "job_abc123", "status": "queued"}
```

Poll with: `python3 scripts/poll_job.py enrichment job_abc123 --timeout 900`

Or manually: `GET /job-status/{task_id}`


## Company Intelligence

### POST /company-intelligence (sync)

```bash
curl -X POST "$API_URL/company-intelligence" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "target_company": {
      "company_name": "Stripe",
      "website": "stripe.com"
    },
    "struct": {
      "revenue_estimate": "Estimated annual revenue in USD",
      "employee_count": "Total number of employees",
      "funding_total": "Total funding raised",
      "tech_stack": "Key technologies used"
    },
    "find_people": true,
    "people_focus_prompt": "C-suite executives and VP-level leaders",
    "tier": "low"
  }'
```

**target_company**: `company_name` (required), plus optional `website`, `linkedin_url`, `domain`.

**find_people**: Discover associated people at the company.

**full_org_chart**: Get department-grouped org chart.

**people_focus_prompt**: Filter which people to find (e.g. "engineering leadership").

**lead_struct**: Custom schema for discovered people (same format as `struct`).

**tier**: Same options as people intelligence (`micro`, `low`, `medium`, `high`).

### POST /company-intelligence-async

Same parameters → poll with `GET /job-status/{task_id}`


## Bulk Intelligence

For running full people/company intelligence (the `struct`-based research agent, not just email/phone) across many records in one call, upload a file instead of building a workflow.

### POST /bulk-intelligence/people

```bash
curl -X POST "$API_URL/bulk-intelligence/people" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -F "file=@leads.csv;type=text/csv" \
  -F 'config={"struct":{"email":"Work email address","title":"Current job title"},"tier":"low"};type=application/json'
```

- **file**: CSV, JSON, JSONL, or NDJSON — max 100 MB / 100,000 rows.
- **config**: JSON-encoded string (not a nested object) with:
  - `struct` (required) — same field-description format as `/people-intelligence`
  - `tier` — same options as people intelligence (`micro`, `low`, `medium`, `high`)
  - `research_plan`, `field_confidence`, `columns` (subset of uploaded columns to use), `webhook_url` (HTTPS callback on completion), `save_json`

**Response:** `{"task_id": "...", "status": "RUNNING", "row_count": 500, "estimated_cost_cents": 2500}`

Poll with: `python3 scripts/poll_job.py enrichment TASK_ID --timeout 3600`. On completion, `GET /job-status/{task_id}` includes signed download links and `charge_amount` (total cents actually charged). Row-level failures pass through un-enriched rather than failing the whole run.

### POST /bulk-intelligence/company

Same shape, config uses `CompanyBulkIntelligenceConfig`:

```bash
curl -X POST "$API_URL/bulk-intelligence/company" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -F "file=@companies.csv;type=text/csv" \
  -F 'config={"struct":{"revenue_estimate":"Estimated annual revenue"},"find_people":true,"people_focus_prompt":"VP Sales, Head of Sales","tier":"low"};type=application/json'
```

Additional `config` fields: `find_people`, `people_focus_prompt`, `lead_struct` (schema for discovered people), `full_org_chart`.

**When to use bulk vs. workflows:** Use bulk intelligence when you just need one enrichment pass over a file (fastest path, no workflow to build/maintain). Use a workflow when you need multiple chained steps — e.g. search → enrich → find_email → filter → notebook.


## Find Email

### POST /find-email

```bash
curl -X POST "$API_URL/find-email" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"lead": {"name": "Jane Doe", "company": "Acme Corp"}}'
```

**Response:**
```json
{
  "name": "Jane Doe",
  "company": "Acme Corp",
  "email": [["jane@acme.com", "OK", "COMPANY"]],
  "cost_cents": 5
}
```

Email array format: `[address, verification_status, type]`
- **Status**: `OK`, `CATCH_ALL`, `RISKY`, `INVALID`
- **Type**: `COMPANY`, `PERSONAL`

**mode** (optional): `"PROFESSIONAL"` (default) or `"PERSONAL"`

### Bulk and async variants

- `POST /find-email-bulk` — array of `leads` (up to 100), returns array of results
- `POST /find-email-async` — returns `task_id`, poll with `GET /job-status/{task_id}`
- `POST /find-email-bulk-async` — bulk + async combined


## Find Phone

### POST /find-phone

```bash
curl -X POST "$API_URL/find-phone" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"lead": {"name": "Jane Doe", "company": "Acme Corp"}}'
```

**Response:** `{"name": "...", "company": "...", "phone": "+1 555-123-4567", "cost_cents": 30}`

Bulk and async variants: `/find-phone-bulk`, `/find-phone-async`, `/find-phone-bulk-async`


## Reverse Lookups

### POST /reverse-email

Given an email, find who it belongs to:

```bash
curl -X POST "$API_URL/reverse-email" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email": "jane@acme.com"}'
```

### POST /reverse-phone

Given a phone number, find who it belongs to:

```bash
curl -X POST "$API_URL/reverse-phone" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"phone": "+15551234567"}'
```

Bulk and async variants available for both.


## Enrich LinkedIn Profile

### POST /enrich-linkedin

Fetch a LinkedIn profile (or company page) and extract structured fields in a single call — cheaper and faster than `/people-intelligence` when you already have the LinkedIn URL and don't need broader web research.

```bash
curl -X POST "$API_URL/enrich-linkedin" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "linkedin_url": "https://linkedin.com/in/janedoe",
    "struct": {
      "title": "Current job title",
      "years_at_company": "How long they have been at their current company"
    }
  }'
```

`struct` is optional — omit it for a default profile extraction. Accepts both personal and company profile URLs.


## Struct Builder

### POST /struct-builder/generate

Not sure what fields to put in `struct`? Describe what you want in plain English and get back a field list to use as your `struct`.

```bash
curl -X POST "$API_URL/struct-builder/generate" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "I need to qualify sales leads: their seniority, whether they have budget authority, and team size",
    "block_type": "lead_enrichment"
  }'
```

**Response:** `{"struct": [{"name": "field_name", "description": "...", "type": "str"}, ...]}`

The response is an array. Intelligence endpoints (`/people-intelligence`, `/company-intelligence`, `/bulk-intelligence/*`) expect `struct` as a plain dict. Convert before use:

```python
struct = {item["name"]: item["description"] for item in response["struct"]}
```

`block_type` (optional) tailors output to the target context: `lead_enrichment`, `company_enrichment`, `linkedin_enrichment`, `research_agent`, `webhook`, `transform_data`. Pass `existing_struct` to extend an existing struct rather than starting fresh.


## Account

### GET /check-balance

Check the org's current credit balance before running a large job:

```bash
curl "$API_URL/check-balance" -H "x-api-key: $SIXTYFOUR_API_KEY"
```

**Response:** `{"credits": 4820.5}`


## QA Agent

### POST /qa-agent

Evaluate and qualify data against criteria using autonomous research:

```bash
curl -X POST "$API_URL/qa-agent" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "lead_info": {"full_name": "Jane Doe", "company": "Acme Corp"},
    "criteria": "Is this person a decision-maker in engineering with budget authority?"
  }'
```

Async variant: `POST /qa-agent-async` → poll with `GET /job-status/{task_id}`


## Tiers and access

The `tier` parameter controls research depth across all intelligence endpoints (people, company, and bulk). Full descriptions are in the main SKILL.md. Summary:

| Tier | When to use | Access |
|------|-------------|--------|
| `micro` | Fastest, lowest cost — single structured source lookup only. Use when speed and cost are critical and fields are very simple (e.g. just an email or title from a known company). Expect lower coverage than `low`. | All plans |
| `low` | Standard fields, clear online presence, high-volume enrichment | All plans |
| `medium` | Incomplete low results, common names, niche profiles, fields requiring synthesis | All plans |
| `high` | AML, KYC/KYB, fraud, due diligence, background checks — exhaustive, no time cap | Enterprise only |

Start with `low`. If results are incomplete or the task demands higher confidence, use `medium`. Use `high` only for investigative and compliance workflows where thoroughness outweighs speed.

If a `high` tier request returns a 403, the user needs enterprise access. Direct them to book a call: https://cal.com/team/sixtyfour/discovery

For `high` tier, prefer the async endpoint (`POST /people-intelligence-async`) with the polling script, since investigations can run for extended periods.


## Typical response times

The API will always return a response — no client-side timeouts needed.

| Endpoint | Tier | Typical time |
|----------|------|-------------|
| find-email, find-phone | — | 2-10s |
| reverse-email, reverse-phone | — | 2-10s |
| people/company-intelligence | low | 10-60s |
| people/company-intelligence | medium | 30-180s |
| people/company-intelligence | high | minutes (no cap — agent investigates until done) |
| qa-agent | — | 30-180s |


## Legacy endpoints — do not use

The spec still lists older endpoints kept for backward compatibility. Always prefer the ones documented above:

| Legacy (don't use) | Use instead |
|---------------------|-------------|
| `/enrich-lead`, `/enrich-lead-async` | `/people-intelligence` (`-async`) |
| `/enrich-company*`, `/enrich-company-v2*` | `/company-intelligence` (`-async`) |
| `/find-email-v2*`, `/find-phone-v2*` | `/find-email*`, `/find-phone*` (non-v2) |
| `/get-linkedin` | `/enrich-linkedin` |
| `/research-agent`, `/research-agent-async` | `people-intelligence`/`company-intelligence`, or the `research_agent` workflow block |

If a stale example references one of these paths, redirect to its replacement.
