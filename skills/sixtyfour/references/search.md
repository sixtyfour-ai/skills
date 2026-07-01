# Search API Reference

Two search modes: **Deep Search** (natural language, agentic — async, poll for results) and **Filter Search** (structured queries — use `POST /search/query` for a synchronous response, or `POST /search/start-filter-search` for the async variant).

## Deep Search

Natural language queries against 500M+ people and 50M+ companies.

### Start: POST /search/start-deep-search

```bash
API_URL="${SIXTYFOUR_API_ENDPOINT:-https://api.sixtyfour.ai}"

curl -X POST "$API_URL/search/start-deep-search" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "VP of Engineering at Series B SaaS startups in New York",
    "mode": "people",
    "max_results": 500
  }'
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| query | string | yes | — | Natural language description of who/what to find |
| mode | string | no | "people" | `"people"` or `"company"` |
| max_results | int | no | 1000 | Result cap |
| output_mode | string | no | "csv" | `"csv"` or `"query_only"` |
| exclude_public_ids | string[] | no | — | People-mode: LinkedIn public IDs/profile URLs to drop (max 1000) |
| exclude_entity_ids | string[] | no | — | Company-mode: numeric company IDs, LinkedIn company URLs/slugs, or exact domains to drop (max 1000) |
| exclude_list_ids | string[] | no | — | Saved exclusion list IDs to apply as a post-filter (max 5) — see [Exclusion Lists](#exclusion-lists) |

**Response:** `{"task_id": "...", "status": "queued"}`

Max 5 concurrent searches per org. Additional requests get 429.

### Poll: GET /search/status/{task_id}

```bash
python3 scripts/poll_job.py search TASK_ID --output /tmp/results.csv
```

Or manually:

```bash
curl "$API_URL/search/status/$TASK_ID" -H "x-api-key: $SIXTYFOUR_API_KEY"
```

Response fields:
- `status`: `queued` | `running` | `completed` | `failed`
- `resource_handle_id`: for CSV download (when completed)
- `total_results`: result count
- `progress_message`: human-readable status
- `iterations`: array of `{iteration, results, elapsed_ms, message}`

Poll every 10-15 seconds. Typical deep searches take 30-120 seconds.

### Download: GET /search/download

```bash
curl "$API_URL/search/download?resource_handle_id=$RHID" -H "x-api-key: $SIXTYFOUR_API_KEY"
```

Returns `{"url": "SIGNED_URL"}` — expires in 15 minutes. Download the CSV from the signed URL.


## Filter Search

Structured queries with field-level filters, pagination, and export.

### Start: POST /search/start-filter-search

```bash
curl -X POST "$API_URL/search/start-filter-search" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "company",
    "simple_filters": {
      "hq_country_iso2": {"$eq": "US"},
      "employees_count": {"$gte": 50, "$lte": 500},
      "industry": {"$in": ["Software", "SaaS"]}
    },
    "max_results": 1000
  }'
```

Returns `{"task_id": "...", "status": "queued"}` — poll the same way as deep search.

### Simple filter operators

| Operator | Description | Example |
|----------|-------------|---------|
| `$eq` | Equals | `{"country": {"$eq": "US"}}` |
| `$ne` | Not equals | `{"status": {"$ne": "inactive"}}` |
| `$in` | In list | `{"industry": {"$in": ["SaaS", "Fintech"]}}` |
| `$nin` | Not in list | `{"industry": {"$nin": ["Government"]}}` |
| `$gt`, `$gte` | Greater than (or equal) | `{"employees_count": {"$gte": 50}}` |
| `$lt`, `$lte` | Less than (or equal) | `{"employees_count": {"$lte": 500}}` |
| `$match` | Wildcard match | `{"title": {"$match": "*engineer*"}}` |
| `$phrase` | Exact phrase | `{"title": {"$phrase": "VP Sales"}}` |
| `$search` | Full text search | `{"bio": {"$search": "machine learning"}}` |
| `$exists` | Field exists | `{"email": {"$exists": true}}` |
| `$and`, `$or`, `$not` | Logical combinators | See below |

### Logical combinators

```json
{
  "$or": [
    {"title": {"$match": "*VP*"}},
    {"title": {"$match": "*Director*"}}
  ],
  "hq_country_iso2": {"$eq": "US"}
}
```

### Discover available fields

```bash
# What fields can I filter on?
curl "$API_URL/search/filter-capabilities" -H "x-api-key: $SIXTYFOUR_API_KEY"

# What are the top values for a specific field?
curl -X POST "$API_URL/search/filter-field-values" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"mode": "company", "field": "industry", "top_k": 25}'
```

Always call `filter-capabilities` first to discover which fields are available and what operators they support. Call `filter-field-values` to see real values before building filters — this avoids typos and shows what the data looks like.


## Exclusion Lists

Build a reusable suppression list (e.g. "existing customers", "do not contact") and apply it across searches via `exclude_list_ids`.

### Create: POST /search/exclusion-lists

Provide exactly one `source`:

```bash
# From inline identifiers (up to 10,000)
curl -X POST "$API_URL/search/exclusion-lists" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Existing customer companies",
    "entity_type": "company",
    "source": {"type": "entity_ids", "entity_ids": ["1441", "linkedin.com/company/openai", "stripe.com"]}
  }'

# From a previous search result
curl -X POST "$API_URL/search/exclusion-lists" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"source": {"type": "search_id", "search_id": "a1b2c3d4-...", "max_results": 250000}}'

# From an uploaded CSV (resource_handle)
curl -X POST "$API_URL/search/exclusion-lists" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Existing customers",
    "entity_type": "person",
    "source": {"type": "resource_handle", "resource_handle_id": "8f14e45f-...", "id_column": "linkedin_url"}
  }'
```

- `entity_type`: `"person"` (default) or `"company"` — must match the search mode you'll apply it to.
- Lists are **immutable** — to change one, create a new list and delete the old. Max 20 active lists per org.
- Materialization is async: `POST` returns `{"id": "...", "status": "pending"}` immediately. Poll `GET /search/exclusion-lists/{id}` until `status` is `"ready"` before using it.

### List / get / delete

```bash
curl "$API_URL/search/exclusion-lists" -H "x-api-key: $SIXTYFOUR_API_KEY"
curl "$API_URL/search/exclusion-lists/$LIST_ID" -H "x-api-key: $SIXTYFOUR_API_KEY"
curl -X DELETE "$API_URL/search/exclusion-lists/$LIST_ID" -H "x-api-key: $SIXTYFOUR_API_KEY"
```

Status values: `pending | materializing | ready | failed`. `size` shows unique member count once ready.

### Applying a list

Pass the list ID(s) in `exclude_list_ids` on `/search/start-deep-search`, `/search/query`, or `/search/export` (max 5 per request, entity type must match search mode):

```json
{"query": "VP Sales at Series B SaaS companies", "mode": "people", "exclude_list_ids": ["LIST_ID"]}
```


## Unified Search Query

### POST /search/query

Replaces `/search/start-filter-search` for structured queries — prefer this for new integrations. Key differences:

- **Synchronous** — returns results directly, no polling needed.
- **Cursor-based pagination** built in.
- Native `exclude_public_ids` / `exclude_entity_ids` / `exclude_list_ids` support.
- Accepts one of: `simple_filters` (MongoDB-style), `filters` (raw OpenSearch DSL), `parsed_query` (replay a previous structured query), or `search_id` (replay a saved search).

```bash
curl -X POST "$API_URL/search/query" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "company",
    "simple_filters": {
      "hq_country_iso2": {"$eq": "US"},
      "employees_count": {"$gte": 50, "$lte": 500}
    },
    "page_size": 50,
    "max_results": 1000,
    "exclude_list_ids": ["LIST_ID"]
  }'
```

**Response:** `{"search_id": "...", "csv_download_url": "...", "json_download_url": "...", "next_cursor": "...", "has_more": true, ...}`

To page: send `{"cursor": "<next_cursor>"}` alone — no need to repeat filters. Rely on `has_more`/`next_cursor`, not page fullness (pages can be smaller than `page_size` when exclusions are active).

People-mode also accepts a natural-language `query` field (mutually exclusive with filter sources) — same idea as deep search but synchronous and paginated.


## Exporting search results

### POST /search/export

Export a previous search to CSV:

```bash
curl -X POST "$API_URL/search/export" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"search_id": "SEARCH_ID", "mode": "people", "max_results": 5000}'
```

Returns `{"task_id": "...", "status": "running"}` — poll with `/search/status/{task_id}`.


## Tips

- Deep search is best for natural language queries where you'd describe the people/companies in plain English
- For structured filter queries, prefer `/search/query` (synchronous, cursor pagination, native exclusions) over the older `/search/start-filter-search`
- Use `filter-capabilities` and `filter-field-values` before building filter queries
- Build an exclusion list once (existing customers, do-not-contact) and reuse via `exclude_list_ids` instead of re-pasting inline IDs on every search
- Max 5000 results per export
- Max 5 concurrent deep searches per org
