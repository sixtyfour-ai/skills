# Example Flows

End-to-end examples showing how to use Sixtyfour for common tasks. Each example shows the complete flow from request to result.

All examples assume:
```bash
API_URL="${SIXTYFOUR_API_ENDPOINT:-https://api.sixtyfour.ai}"
```

---

## 1. Find someone's email (simplest case)

**User**: "What's the email for Jane Doe at Acme Corp?"

```bash
curl -s -X POST "$API_URL/v1/people/contacts" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"person": {"name": "Jane Doe", "company": "Acme Corp"}, "find": ["work_email"], "wait_seconds": 20}'
```

The response is a Job. When `status` is `succeeded`, read `result.email` and `result.email_status` (`OK` is verified; `NOT_FOUND` means no address). If the response is `202` with `status: "running"`, poll it: `python3 scripts/poll_job.py JOB_ID`.

---

## 2. Research a company

**User**: "Research Ramp — revenue, headcount, funding, engineering leadership"

```bash
curl -s -X POST "$API_URL/v1/companies/intelligence" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "company": {"name": "Ramp", "website": "ramp.com"},
    "tier": "low",
    "fields": {
      "revenue_estimate": "Estimated annual revenue",
      "employee_count": {"type": "int", "description": "Total employees"},
      "funding_history": "Funding rounds with amounts and lead investors"
    },
    "find_people": true,
    "people_focus_prompt": "Engineering leadership",
    "wait_seconds": 20
  }'
```

Poll the returned `job_id`, then read `GET /v1/jobs/JOB_ID/items`: the fields are in `items[0].result` and the people in `items[0].result.leads`.

---

## 3. Natural language search — build a prospect list

**User**: "Find 500 VPs of Sales at Series B SaaS startups in NYC"

### Step 1: Start the search

```bash
curl -s -X POST "$API_URL/v1/people/search" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "VP of Sales at Series B SaaS startups in New York City", "max_results": 500, "wait_seconds": 0}'
```

### Step 2: Poll and download

```bash
python3 scripts/poll_job.py JOB_ID --output /tmp/vp_sales.csv
```

### Step 3: Use the results

Read the CSV and summarize it for the user. For emails or deeper fields on these people, pass the search Job to a workflow or send the rows as `people` to `/v1/people/contacts` or `/v1/people/intelligence`.

---

## 4. Filter search — structured criteria

**User**: "Find US software companies with 50-500 employees"

### Step 1: Discover available field values

```bash
# What values exist for the industry field?
curl -s -X POST "$API_URL/v1/companies/search/field-values" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"field": "industry", "max_results": 25}'
```

### Step 2: Run the filter search

```bash
curl -s -X POST "$API_URL/v1/companies/search" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "filters": {
      "hq_country_iso2": {"$eq": "US"},
      "employees_count": {"$gte": 50, "$lte": 500},
      "industry": {"$in": ["Software Development"]}
    },
    "max_results": 1000,
    "wait_seconds": 20
  }'
```

### Step 3: Poll and download

```bash
python3 scripts/poll_job.py JOB_ID --output /tmp/companies.csv
```

---

## 5. Workflow — search, enrich, get emails at scale

**User**: "Find engineering managers at top AI startups and get their emails and LinkedIn profiles"

### Step 1: Create the workflow

```bash
curl -s -X POST "$API_URL/v1/workflows" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "AI Startup Engineering Managers",
    "description": "Find engineering managers at AI startups, enrich profiles, get emails",
    "definition": {
      "blocks": [
        {
          "sequence_number": 1, "block_name": "search", "block_type": "search", "block_id": "source",
          "specs": {"query": "Engineering Manager at OpenAI, Anthropic, Cohere, Mistral, Databricks, Scale AI, Hugging Face", "dataframe_type": "LEAD", "max_results": 300, "auto_execute": true}
        },
        {
          "sequence_number": 2, "block_name": "deduplicate", "block_type": "deduplicate", "block_id": "dedup",
          "specs": {}
        },
        {
          "sequence_number": 3, "block_name": "lead_enrichment", "block_type": "lead_enrichment", "block_id": "enrich",
          "specs": {"return_fields": {
            "linkedin_url": {"description": "LinkedIn profile URL", "type": "str"},
            "years_at_company": {"description": "Years at current company", "type": "int"},
            "previous_companies": {"description": "Previous companies worked at", "type": "list[str]"}
          }}
        },
        {
          "sequence_number": 4, "block_name": "find_email", "block_type": "find_email", "block_id": "emails",
          "specs": {"mode": "PROFESSIONAL"}
        },
        {
          "sequence_number": 5, "block_name": "filter", "block_type": "filter", "block_id": "valid_emails",
          "specs": {"filters": [{"column": "email_status", "operator": "equals", "value": "OK"}]}
        },
        {
          "sequence_number": 6, "block_name": "append_to_notebook", "block_type": "append_to_notebook", "block_id": "save",
          "specs": {"notebook_id": "__create_new__", "notebook_name": "AI Startup Engineering Managers"}
        }
      ],
      "edges": [
        {"from_block_id": "source", "to_block_id": "dedup"},
        {"from_block_id": "dedup", "to_block_id": "enrich"},
        {"from_block_id": "enrich", "to_block_id": "emails"},
        {"from_block_id": "emails", "to_block_id": "valid_emails"},
        {"from_block_id": "valid_emails", "to_block_id": "save"}
      ]
    }
  }'
```

Read `workflow_id` from the response.

### Step 2: Run the workflow

```bash
curl -s -X POST "$API_URL/v1/workflows/WORKFLOW_ID/runs" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{}'
```

The response is a Job. This workflow's source is a search block, so the run needs no `input`.

### Step 3: Poll and download

```bash
python3 scripts/poll_job.py JOB_ID --timeout 1800 --output /tmp/ai_eng_managers.csv
```

---

## 6. Workflow — enrich an existing list (webhook input)

**User**: "I have a list of 200 leads — get their work emails and titles"

### Step 1: Create the workflow

```bash
curl -s -X POST "$API_URL/v1/workflows" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Enrich my leads",
    "description": "Find work emails and titles for a list of leads",
    "definition": {
      "blocks": [
        {"sequence_number": 1, "block_name": "webhook", "block_type": "webhook", "block_id": "input", "specs": {}},
        {"sequence_number": 2, "block_name": "lead_enrichment", "block_type": "lead_enrichment", "block_id": "enrich",
          "specs": {"return_fields": {"title": {"description": "Current job title", "type": "str"}}}},
        {"sequence_number": 3, "block_name": "find_email", "block_type": "find_email", "block_id": "emails", "specs": {"mode": "PROFESSIONAL"}}
      ],
      "edges": [
        {"from_block_id": "input", "to_block_id": "enrich"},
        {"from_block_id": "enrich", "to_block_id": "emails"}
      ]
    }
  }'
```

### Step 2: Run with your data

```bash
curl -s -X POST "$API_URL/v1/workflows/WORKFLOW_ID/runs" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"input": [
    {"full_name": "Jane Doe", "company": "Acme Corp"},
    {"full_name": "John Smith", "company": "Globex Inc"}
  ]}'
```

### Step 3: Poll and download

```bash
python3 scripts/poll_job.py JOB_ID --timeout 1800 --output /tmp/enriched_leads.csv
```

For a single pass with no chained steps, skip the workflow: send the rows as `people` to `/v1/people/contacts` or `/v1/people/intelligence`.

---

## 7. Reverse lookup — who owns this email?

**User**: "Who is jane@acme.com?"

```bash
curl -s -X POST "$API_URL/v1/people/contacts/reverse" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email": "jane@acme.com", "wait_seconds": 20}'
```

When the Job is `succeeded`, `result` holds the profile (`firstname`, `lastname`, `title`, `company_name`, `linkedin_url`). With no match, `result.email_error` is `"No data found"`.

---

## 8. Company research pipeline — companies + their people + contact info

**User**: "Research these 3 fintech companies, find their heads of engineering, and get their emails"

### Step 1: Research the companies and find people

```bash
curl -s -X POST "$API_URL/v1/companies/intelligence" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "companies": [
      {"name": "Ramp", "website": "ramp.com"},
      {"name": "Brex", "website": "brex.com"},
      {"name": "Mercury", "website": "mercury.com"}
    ],
    "tier": "low",
    "fields": {"employee_count": {"type": "int", "description": "Total employees"}, "funding_total": "Total funding raised"},
    "find_people": true,
    "people_focus_prompt": "Head of Engineering, VP Engineering, CTO",
    "wait_seconds": 0
  }'
```

### Step 2: Read the companies and their people

```bash
python3 scripts/poll_job.py JOB_ID
curl -s "$API_URL/v1/jobs/JOB_ID/items" -H "x-api-key: $SIXTYFOUR_API_KEY"
```

Each item's `result.leads` lists the people found.

### Step 3: Get contact info for the people

```bash
curl -s -X POST "$API_URL/v1/people/contacts" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "people": [
      {"name": "PERSON_NAME", "company": "Ramp"},
      {"name": "PERSON_NAME", "company": "Brex"}
    ],
    "find": ["work_email", "phone"],
    "wait_seconds": 20
  }'
```

Read the rows from `GET /v1/jobs/JOB_ID/items`.

---

## 9. Age verification — KYC/compliance check

**User**: "Verify this person is over 18: Jane Doe at Acme Corp"

### Step 1: Start the verification

```bash
curl -s -X POST "$API_URL/v1/people/age-verification" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "person": {"name": "Jane Doe", "company": "Acme Corp", "linkedin": "https://www.linkedin.com/in/janedoe"},
    "wait_seconds": 0
  }'
```

### Step 2: Poll for the result

```bash
python3 scripts/poll_job.py JOB_ID
```

The finished Job's `result` has `date_of_birth`, `age` (`value`, `as_of`, `confidence` 0 to 100), `evidence` and `sources`. Report the confidence and sources along with the answer; send low-confidence results to a human.

---

## 10. Schedule a recurring workflow

**User**: "Run my lead refresh workflow every weekday at 9am Eastern"

### Step 1: Create the schedule (workflow must already exist)

```bash
curl -s -X POST "$API_URL/v1/schedules" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "WORKFLOW_ID",
    "name": "Weekday lead refresh",
    "cron_expression": "0 9 * * 1-5",
    "timezone": "America/New_York"
  }'
```

The response includes `schedule_id` and `next_run_times`.

### Step 2 (optional): Pause or update later

```bash
curl -s -X PATCH "$API_URL/v1/schedules/SCHEDULE_ID" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'
```
