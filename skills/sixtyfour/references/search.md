# Search API Reference

Two search modes: **Deep Search** (natural language, agentic) and **Filter Search** (structured queries). Both are async — start a search, poll for status, download results.

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
- Filter search is best when you know the exact fields and values you want (industry, location, headcount range)
- Use `filter-capabilities` and `filter-field-values` before building filter queries
- Max 5000 results per export
- Max 5 concurrent deep searches per org
