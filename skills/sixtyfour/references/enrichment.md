# Enrichment API Reference

All routes are under `/v1` and return a Job unless noted. See "How every request works" in the main SKILL.md for `wait_seconds`, polling and errors.

```bash
API_URL="${SIXTYFOUR_API_ENDPOINT:-https://api.sixtyfour.ai}"
```

## People Intelligence

Research a person and return any fields you define. `fields` is fully flexible — describe any fields and the AI research agent will find them.

### POST /v1/people/intelligence

```bash
curl -X POST "$API_URL/v1/people/intelligence" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "person": {
      "name": "Jane Doe",
      "company": "Acme Corp",
      "linkedin_url": "https://linkedin.com/in/janedoe"
    },
    "tier": "low",
    "fields": {
      "title": "Current job title",
      "years_experience": {"type": "int", "description": "Total years of professional experience"},
      "skills": {"type": "list[str]", "description": "Key technical skills"}
    },
    "wait_seconds": 20
  }'
```

Send exactly one of `person`, `people` or `input_file_id`.

**person** — any attributes you know; more gives better matching: `name`, `company`, `email`, `linkedin_url`, `location`.

**people** — 1 to 100,000 person objects. Set `custom_id` on each record to match results to your own rows.

**input_file_id** — the `file_id` of an uploaded file of people (see [Files](#files)).

**fields** (required) — `field_name: description`, or `field_name: {"type", "description"}`. The description guides the agent — be specific about what you want ("The person's primary work email", not "email").

**tier** (required) — controls research depth:
- `micro`: Fastest, cheapest lookup. Up to 10 simple fields on well-indexed subjects. Lower coverage than `low`.
- `low`: Fast single-pass across well-indexed public sources. Good for standard fields (title, company, LinkedIn) with clear online presence.
- `medium`: Multi-source deep research with cross-referencing. Use when `low` comes back incomplete, subject is hard to find, or task needs higher confidence.
- `high`: Exhaustive OSINT-grade investigation. Use for AML, KYC/KYB, fraud, due diligence. Available on request — if 403, direct user to https://cal.com/team/sixtyfour/discovery

**research_plan** (optional): A string guiding the research strategy (e.g. "Focus on public filings and press mentions").

**webhook_url** (optional): HTTPS URL to notify when the Job finishes.

**Response:** a Job. When `status` is `succeeded`, read the rows:

```bash
curl "$API_URL/v1/jobs/$JOB_ID/items?page_size=100" -H "x-api-key: $SIXTYFOUR_API_KEY"
```

```json
{
  "items": [
    {
      "index": 0,
      "custom_id": null,
      "input": {"name": "Jane Doe", "company": "Acme Corp"},
      "status": "succeeded",
      "result": {
        "name": "Jane Doe",
        "company": "Acme Corp",
        "title": "VP Engineering",
        "years_experience": 12,
        "skills": ["Python", "Postgres"],
        "enrichment_references": {"https://linkedin.com/in/janedoe": "LinkedIn profile"},
        "enrichment_confidence_score": 9
      },
      "error": null
    }
  ],
  "next_cursor": null
}
```

Pass `next_cursor` back as `cursor` until it is null. A finished batch can contain failed items; check each item's `status`.

Or wait with the script: `python3 scripts/poll_job.py JOB_ID --output /tmp/people.csv`


## Company Intelligence

### POST /v1/companies/intelligence

```bash
curl -X POST "$API_URL/v1/companies/intelligence" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "company": {"name": "Stripe", "website": "stripe.com"},
    "tier": "low",
    "fields": {
      "revenue_estimate": "Estimated annual revenue in USD",
      "employee_count": {"type": "int", "description": "Total number of employees"},
      "funding_total": "Total funding raised",
      "tech_stack": "Key technologies used"
    },
    "find_people": true,
    "people_focus_prompt": "C-suite executives and VP-level leaders",
    "wait_seconds": 20
  }'
```

Send exactly one of `company`, `companies` (up to 100,000) or `input_file_id`.

**find_people**: Discover people at the company. They come back in the item's `result.leads` (`name`, `title`, `company`, `email`, `phone`, `linkedin`, `location`, `score`).

**people_focus_prompt**: Which people to find (e.g. "engineering leadership").

**tier**, **fields**, **research_plan**, **webhook_url**: same as people intelligence.

Read results from `GET /v1/jobs/{job_id}/items`, as above.


## Files

Upload a CSV, JSON or NDJSON file once and use its `file_id` as `input_file_id` on contacts, reverse lookup or intelligence requests:

```bash
FILE_ID=$(curl -sS "$API_URL/v1/files" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -F "file=@leads.csv;type=text/csv" | jq -r .file_id)

curl -X POST "$API_URL/v1/people/intelligence" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"input_file_id\": \"$FILE_ID\", \"tier\": \"low\", \"fields\": {\"title\": \"Current job title\"}, \"wait_seconds\": 0}"
```

`GET /v1/files/{file_id}` returns the file's metadata and a signed `download_url` that is valid for 15 minutes; read the file again to refresh it.

**When to use a batch vs. workflows:** Use a batch when you need one enrichment pass over a file or list (fastest path, no workflow to build/maintain). Use a workflow when you need multiple chained steps — e.g. search → enrich → find_email → filter → notebook.


## Find Contacts

Find work emails, personal emails and phone numbers for leads for sales outreach, CRM enrichment, or lead qualification. Use this for any email or phone request instead of a field in people intelligence `fields`.

### POST /v1/people/contacts

```bash
curl -X POST "$API_URL/v1/people/contacts" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "person": {"name": "Jane Doe", "company": "Acme Corp"},
    "find": ["work_email", "phone"],
    "wait_seconds": 20
  }'
```

**find** (required): 1 to 3 of `work_email`, `personal_email`, `phone`.

**verify_emails** (optional, default `true`): if `false`, returns the first address with `UNKNOWN` status.

Send exactly one of `person`, `people` (up to 100,000) or `input_file_id`.

**Response** — a Job. For a single person, the finished Job carries the answer in `result`:

```json
{
  "job_id": "job_e07337e2-...",
  "status": "succeeded",
  "operation": "people.contacts",
  "counts": {"total": 1, "succeeded": 1, "failed": 0, "pending": 0},
  "charge_credits": 0.5,
  "result": {
    "name": "Jane Doe",
    "company": "Acme Corp",
    "email": "jane@acme.com",
    "email_status": "OK",
    "email_type": "COMPANY",
    "other_emails": [],
    "phone": "+15551234567"
  }
}
```

- **Email status**: `OK` (verified), `RISKY` (domain accepts all mail), `INVALID`, `UNKNOWN`, `NOT_FOUND`
- Personal emails come back as `personal_email`, `personal_email_status`, `personal_email_type`.
- A missing email or phone is an empty string. `NOT_FOUND` describes the answer; the Job still `succeeded`.

For `people` or `input_file_id`, read rows from `GET /v1/jobs/{job_id}/items`.


## Reverse Lookup

### POST /v1/people/contacts/reverse

Given an email or a phone number, find who it belongs to. Send exactly one of `email` or `phone`:

```bash
curl -X POST "$API_URL/v1/people/contacts/reverse" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email": "jane@acme.com", "wait_seconds": 20}'

curl -X POST "$API_URL/v1/people/contacts/reverse" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"phone": "+15551234567", "wait_seconds": 20}'
```

A finished single lookup carries the profile in `result` (`firstname`, `lastname`, `title`, `linkedin_url`, `location`, `company_name`, `company_domain`, ...). For many lookups, send `items` (up to 100,000, one contact type per request) or `input_file_id`, and read `GET /v1/jobs/{job_id}/items`.


## Verify Email

### POST /v1/verify/emails

```bash
curl -X POST "$API_URL/v1/verify/emails" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email": "jane@acme.com"}'
```

**Response** (returned directly, not a Job): `{"email": "jane@acme.com", "status": "valid", "score": 100}`

`status` is lowercase here: `valid`, `risky`, `invalid` or `unknown`.


## Account

### GET /v1/balance

Check the org's current credit balance before running a large job:

```bash
curl "$API_URL/v1/balance" -H "x-api-key: $SIXTYFOUR_API_KEY"
```

**Response:** `{"credits": 4820.5}`


## Age Verification

Establish a person's date of birth (or a grounded age estimate) from open-source research, with confidence scores and sourced evidence. Use for trust-and-safety, KYC, and due-diligence workflows where self-reported age isn't enough.

### POST /v1/people/age-verification

```bash
curl -X POST "$API_URL/v1/people/age-verification" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "person": {
      "name": "Jane Doe",
      "company": "Acme Corp",
      "linkedin": "https://www.linkedin.com/in/janedoe"
    },
    "wait_seconds": 0
  }'
```

**person** — any identifiers you have (name, company, linkedin, email, location, etc.); more is better.

A verification takes minutes, so the response is a running Job. Poll it: `python3 scripts/poll_job.py JOB_ID`

**`result` once the Job is `succeeded`:**
```json
{
  "date_of_birth": {"day": 14, "month": 3, "year": 1990, "confidence": 82},
  "age": {"value": 36, "as_of": "2026-07-31", "confidence": 80},
  "evidence": "Summary of what evidence established the date of birth or age.",
  "sources": ["https://..."]
}
```

Each `date_of_birth` component (`day`/`month`/`year`) is `null` unless a concrete source establishes it (never guessed). `age.value` may still be populated as a grounded estimate even when the exact date of birth isn't fully known. Confidence is 0 to 100.

Age Verification needs no tier access: any organization with credits can call it.


## Tiers and access

`tier` is required on every intelligence request. Full descriptions are in the main SKILL.md. Summary:

| Tier | When to use | Access |
|------|-------------|--------|
| `micro` | Fastest, lowest cost. Use when speed and cost are critical and fields are very simple (e.g. just a title or company for a known person). Expect lower coverage than `low`. | All organizations |
| `low` | Standard fields, clear online presence, high-volume enrichment | All organizations |
| `medium` | Incomplete low results, common names, niche profiles, fields requiring synthesis | All organizations |
| `high` | AML, KYC/KYB, fraud, due diligence, background checks — exhaustive | On request |

Start with `low`. If results are incomplete or the task demands higher confidence, use `medium`. Use `high` only for investigative and compliance workflows where thoroughness outweighs speed.

If a `high` tier request returns a 403, the user needs access. Direct them to book a call: https://cal.com/team/sixtyfour/discovery

For `medium` and `high`, send `"wait_seconds": 0` and use the polling script, since investigations can run for extended periods.


## Typical response times

`wait_seconds` tops out at 20, so anything slower returns a running Job to poll.

| Endpoint | Tier | Typical time |
|----------|------|-------------|
| contacts, reverse lookup | — | 2-10s |
| people/company intelligence | low | 10-60s |
| people/company intelligence | medium | 30-180s |
| people/company intelligence | high | minutes |
| age verification | — | minutes |


## Original routes — do not use for new code

Unversioned routes (`/find-email`, `/people-intelligence`, `/job-status/{task_id}`, `/verify-age`, ...) and the `/v1/find-email`-style aliases keep working for existing integrations, with their original bodies and status names. Always write new code against the routes above. If a stale example references an original route, find its replacement in the route table:

```bash
curl -s "https://docs.sixtyfour.ai/api-reference/legacy.md"
```
