# Search API Reference

One route per record type finds people or companies: `POST /v1/people/search` and `POST /v1/companies/search`. Each start takes exactly one of:

- `query` — natural language, agentic search
- `filters` — structured, field-level filters
- `seeds` — example people to find lookalikes for (people search only, up to 1,000)
- `search_id` — replay a saved search

Every start returns a Job. Read its rows from `GET /v1/jobs/{job_id}/items`, or export them to a file.

```bash
API_URL="${SIXTYFOUR_API_ENDPOINT:-https://api.sixtyfour.ai}"
```

## Natural language search

```bash
curl -X POST "$API_URL/v1/people/search" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "VP of Engineering at Series B SaaS startups in New York",
    "max_results": 500,
    "wait_seconds": 0
  }'
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| query | string | — | Natural language description of who/what to find |
| max_results | int | 10 | Result cap. The fields endpoint reports the allowed maximum |
| exclude_list_ids | string[] | — | Saved list IDs whose members to drop (max 5) — see [Exclusion Lists](#exclusion-lists) |
| wait_seconds | int | 5 | Seconds to wait for the Job, 0 to 20 |
| webhook_url | string | — | HTTPS URL to notify when the Job finishes |

For companies, send the same body to `POST /v1/companies/search`.

**Response:** a Job, e.g. `{"job_id": "job_...", "status": "running", "operation": "people.search", "next_poll_after": 5, ...}`

### Poll and download

```bash
python3 scripts/poll_job.py JOB_ID --output /tmp/results.csv
```

Or manually:

```bash
# Poll until status is succeeded, failed or canceled
curl "$API_URL/v1/jobs/$JOB_ID" -H "x-api-key: $SIXTYFOUR_API_KEY"

# Read rows, 1 to 1,000 per page
curl "$API_URL/v1/jobs/$JOB_ID/items?page_size=100" -H "x-api-key: $SIXTYFOUR_API_KEY"
```

`items` returns `{"items": [...], "next_cursor": "..."}`. Pass `next_cursor` back as `cursor` until it is null. Natural language searches typically take 30-120 seconds.


## Filter Search

Structured queries with field-level filters.

```bash
curl -X POST "$API_URL/v1/companies/search" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "filters": {
      "hq_country_iso2": {"$eq": "US"},
      "employees_count": {"$gte": 50, "$lte": 500},
      "industry": {"$in": ["Software", "SaaS"]}
    },
    "max_results": 1000,
    "wait_seconds": 20
  }'
```

Returns a Job — read it the same way as a natural language search.

### Filter operators

| Operator | Description | Example |
|----------|-------------|---------|
| `$eq`, `$ne` | Equals / not equals | `{"hq_country_iso2": {"$eq": "US"}}` |
| `$in`, `$nin` | In / not in list (1 to 25 values) | `{"industry": {"$in": ["SaaS", "Fintech"]}}` |
| `$gt`, `$gte`, `$lt`, `$lte` | Number or date range | `{"employees_count": {"$gte": 50}}` |
| `$match` | Any word of the value | `{"title": {"$match": "engineer"}}` |
| `$phrase` | Every word of the value | `{"title": {"$phrase": "VP Sales"}}` |
| `$exists` | Field present or absent | `{"email": {"$exists": true}}` |
| `$and`, `$or`, `$nor`, `$not` | Logical combinators | See below |
| `$elemMatch` | Match nested array elements | Keyed by full field paths |

### Logical combinators

```json
{
  "$or": [
    {"title": {"$match": "VP"}},
    {"title": {"$match": "Director"}}
  ],
  "hq_country_iso2": {"$eq": "US"}
}
```

### Discover available fields

```bash
# What fields can I filter on?
curl "$API_URL/v1/companies/search/fields" -H "x-api-key: $SIXTYFOUR_API_KEY"

# What are the top values for a specific field?
curl -X POST "$API_URL/v1/companies/search/field-values" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"field": "industry", "max_results": 25}'
```

Use `/v1/people/search/fields` and `/v1/people/search/field-values` for people. Always read `fields` first to discover which fields are available and what operators they support. Call `field-values` to see real values before building filters — this avoids typos and shows what the data looks like.


## Exclusion Lists

Build a reusable suppression list (e.g. "existing customers", "do not contact") and apply it across searches via `exclude_list_ids`.

### Create: POST /v1/lists

`from` takes exactly one of `ids`, `input_file_id` or `job_id`:

```bash
# From inline identifiers
curl -X POST "$API_URL/v1/lists" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "Existing customer companies", "entity_type": "companies", "from": {"ids": ["linkedin.com/company/openai", "stripe.com"]}}'

# From a finished search Job
curl -X POST "$API_URL/v1/lists" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "Already contacted", "entity_type": "people", "from": {"job_id": "JOB_ID"}}'

# From an uploaded file (POST /v1/files)
curl -X POST "$API_URL/v1/lists" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "Existing customers", "entity_type": "people", "from": {"input_file_id": "FILE_ID"}}'
```

- `entity_type`: `"people"` or `"companies"` — must match the search you apply it to.
- Building is async: the response is `{"list_id": "list_...", "job_id": "job_...", "status": "building"}`. Poll the Job (or `GET /v1/lists/{list_id}`) until the list is ready before using it.
- To change a list, create a new one and delete the old.

### List / get / delete

```bash
curl "$API_URL/v1/lists" -H "x-api-key: $SIXTYFOUR_API_KEY"
curl "$API_URL/v1/lists/$LIST_ID" -H "x-api-key: $SIXTYFOUR_API_KEY"
curl "$API_URL/v1/lists/$LIST_ID/rows" -H "x-api-key: $SIXTYFOUR_API_KEY"
curl -X DELETE "$API_URL/v1/lists/$LIST_ID" -H "x-api-key: $SIXTYFOUR_API_KEY"
```

### Applying a list

Pass the list ID(s) in `exclude_list_ids` on a search (max 5 per request):

```json
{"query": "VP Sales at Series B SaaS companies", "exclude_list_ids": ["LIST_ID"]}
```


## Exporting search results

### POST /v1/exports

Export a finished Job's rows (or a ready list) to CSV, JSON or NDJSON:

```bash
EXPORT_JOB_ID=$(curl -sS -X POST "$API_URL/v1/exports" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"from": {"job_id": "JOB_ID"}, "format": "csv"}' | jq -r .job_id)
```

The export is its own Job. Poll it; when it is `succeeded`, read the file ID from `result.output_file_id`, then download:

```bash
FILE_ID=$(curl -sS "$API_URL/v1/jobs/$EXPORT_JOB_ID" -H "x-api-key: $SIXTYFOUR_API_KEY" | jq -r .result.output_file_id)
URL=$(curl -sS "$API_URL/v1/files/$FILE_ID" -H "x-api-key: $SIXTYFOUR_API_KEY" | jq -r .download_url)
curl -sS "$URL" -H "x-api-key: $SIXTYFOUR_API_KEY" -o results.csv
```

`download_url` is valid for 15 minutes; read the file again to refresh it. `python3 scripts/poll_job.py JOB_ID --output results.csv` does all of this.


## Tips

- Use `query` when you'd describe the people/companies in plain English; use `filters` for exact criteria
- Read `fields` and `field-values` before building filter queries
- Build an exclusion list once (existing customers, do-not-contact) and reuse via `exclude_list_ids`
- An export holds up to 100,000 rows or 100 MB
- Replay a saved search with `{"search_id": "SEARCH_ID", "max_results": 10}`; it starts a new Job
