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
- `low` (default): Fast single-pass lookup across well-indexed sources. Good for standard fields (email, title, LinkedIn) on people/companies with clear online presence.
- `medium`: Multi-source deep research with cross-referencing and verification. Use when low comes back incomplete, the subject is hard to find, or the task needs higher confidence (competitive intel, recruiting, market research).
- `high`: Exhaustive OSINT-grade investigation — official records, proprietary databases, dark web. No time limit; the agent investigates every avenue. Use for AML, KYC/KYB, fraud, due diligence. Requires enterprise access — if 403, direct user to https://cal.com/team/sixtyfour/discovery

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

**tier**: Same tiers as people intelligence.

### POST /company-intelligence-async

Same parameters → poll with `GET /job-status/{task_id}`


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

The `tier` parameter on people-intelligence and company-intelligence controls research depth. Full descriptions are in the main SKILL.md. Summary:

| Tier | When to use | Access |
|------|-------------|--------|
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
