# Example Flows

End-to-end examples showing how to use Sixtyfour for common tasks. Each example shows the complete flow from request to result.

All examples assume:
```bash
API_URL="${SIXTYFOUR_API_ENDPOINT:-https://api.sixtyfour.ai}"
```

---

## 1. Find someone's email (simplest case)

**User**: "Find me the email for Sarah Chen at Figma"

```bash
curl -X POST "$API_URL/find-email" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"lead": {"name": "Sarah Chen", "company": "Figma"}}'
```

Response:
```json
{
  "name": "Sarah Chen",
  "company": "Figma",
  "email": [["sarah@figma.com", "OK", "COMPANY"]],
  "cost_cents": 5
}
```

Done. One request, instant result.

---

## 2. Research a company

**User**: "What can you tell me about Ramp? Revenue, headcount, funding, and who runs engineering?"

```bash
curl -X POST "$API_URL/company-intelligence" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "target_company": {"company_name": "Ramp", "website": "ramp.com"},
    "struct": {
      "annual_revenue": "Estimated annual revenue",
      "employee_count": "Total number of employees",
      "total_funding": "Total funding raised with last round details",
      "tech_stack": "Key technologies and frameworks used"
    },
    "find_people": true,
    "people_focus_prompt": "VP of Engineering, CTO, Head of Engineering, engineering directors",
    "tier": "medium"
  }'
```

Response includes `structured_data` with all requested fields, `notes` with detailed research, and a list of engineering leaders found.

---

## 3. Deep search — build a prospect list

**User**: "Find me 200 VPs of Sales at Series B+ SaaS companies in the Bay Area"

### Step 1: Start the search

```bash
RESPONSE=$(curl -s -X POST "$API_URL/search/start-deep-search" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "VP of Sales at Series B or later SaaS companies in San Francisco Bay Area", "mode": "people", "max_results": 200}')

TASK_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['task_id'])")
echo "Search started: $TASK_ID"
```

### Step 2: Poll and download

```bash
python3 scripts/poll_job.py search "$TASK_ID" --output /tmp/vp_sales_bay_area.csv --timeout 300
```

### Step 3: Use the results

The CSV contains structured profiles. You can inspect it:

```bash
head -5 /tmp/vp_sales_bay_area.csv
```

Or pipe it into a workflow for further enrichment (emails, phones, custom fields).

---

## 4. Filter search — structured criteria

**User**: "Find US SaaS companies with 50-500 employees in the fintech space"

### Step 1: Discover available field values

```bash
# What values exist for the industry field?
curl -s -X POST "$API_URL/search/filter-field-values" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"mode": "company", "field": "industry", "top_k": 50}' | python3 -m json.tool
```

### Step 2: Run the filter search

```bash
RESPONSE=$(curl -s -X POST "$API_URL/search/start-filter-search" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "company",
    "simple_filters": {
      "hq_country_iso2": {"$eq": "US"},
      "employees_count": {"$gte": 50, "$lte": 500},
      "industry": {"$in": ["Financial Services", "Fintech", "Financial Technology"]}
    },
    "max_results": 1000
  }')

TASK_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['task_id'])")
```

### Step 3: Poll and download

```bash
python3 scripts/poll_job.py search "$TASK_ID" --output /tmp/fintech_companies.csv
```

---

## 5. Workflow — search, enrich, get emails at scale

**User**: "Find engineering managers at top AI startups and get their emails and LinkedIn profiles"

### Step 1: Create the workflow

```bash
curl -s -X POST "$API_URL/workflows/create_workflow" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_name": "AI Startup Engineering Managers",
    "workflow_description": "Find engineering managers at AI startups, enrich profiles, get emails",
    "workflow_definition": {
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

Extract the workflow ID from the response.

### Step 2: Run the workflow

The search block with `auto_execute: true` already ran at creation. For webhook-based workflows, you'd run:

```bash
curl -s -X POST "$API_URL/workflows/run?workflow_id=WF_ID" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"webhook_payload": []}'
```

### Step 3: Poll and download

```bash
python3 scripts/poll_job.py workflow RUN_ID --timeout 1800 --output /tmp/ai_eng_managers.csv
```

---

## 6. Workflow — enrich an existing list (webhook input)

**User**: "I have a list of 50 leads. Enrich them with titles, emails, and company revenue."

### Step 1: Create the workflow

```bash
curl -s -X POST "$API_URL/workflows/create_workflow" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_name": "Inbound Lead Enrichment",
    "workflow_description": "Enrich provided leads with title, email, and company revenue",
    "workflow_definition": {
      "blocks": [
        {"sequence_number": 1, "block_name": "webhook", "block_type": "webhook", "block_id": "input", "specs": {}},
        {"sequence_number": 2, "block_name": "lead_enrichment", "block_type": "lead_enrichment", "block_id": "enrich",
         "specs": {"return_fields": {
           "title": {"description": "Current job title", "type": "str"},
           "company_revenue": {"description": "Estimated annual revenue of their company", "type": "str"},
           "linkedin_url": {"description": "LinkedIn profile URL", "type": "str"}
         }}},
        {"sequence_number": 3, "block_name": "find_email", "block_type": "find_email", "block_id": "emails", "specs": {"mode": "PROFESSIONAL"}},
        {"sequence_number": 4, "block_name": "append_to_notebook", "block_type": "append_to_notebook", "block_id": "save",
         "specs": {"notebook_id": "__create_new__", "notebook_name": "Enriched Leads"}}
      ],
      "edges": [
        {"from_block_id": "input", "to_block_id": "enrich"},
        {"from_block_id": "enrich", "to_block_id": "emails"},
        {"from_block_id": "emails", "to_block_id": "save"}
      ]
    }
  }'
```

### Step 2: Run with your data

```bash
RESPONSE=$(curl -s -X POST "$API_URL/workflows/run?workflow_id=WF_ID" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"webhook_payload": [
    {"full_name": "Jane Doe", "company": "Acme Corp"},
    {"full_name": "John Smith", "company": "Globex Inc"},
    {"full_name": "Alice Johnson", "company": "Initech"}
  ]}')

RUN_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['job_id'])")
```

### Step 3: Poll and download

```bash
python3 scripts/poll_job.py workflow "$RUN_ID" --timeout 1800 --output /tmp/enriched_leads.csv
```

---

## 7. Reverse lookup — who owns this email?

**User**: "Who is behind the email cto@startup.io?"

```bash
curl -X POST "$API_URL/reverse-email" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email": "cto@startup.io"}'
```

Returns the person's name, company, title, LinkedIn, and other profile data.

---

## 8. Company research pipeline — companies + their people + contact info

**User**: "Research these 5 companies, find their sales leaders, and get emails"

```bash
curl -s -X POST "$API_URL/workflows/create_workflow" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_name": "Company Research Pipeline",
    "workflow_description": "Research companies, find sales leaders, get emails",
    "workflow_definition": {
      "blocks": [
        {"sequence_number": 1, "block_name": "webhook", "block_type": "webhook", "block_id": "input", "specs": {}},
        {"sequence_number": 2, "block_name": "company_enrichment", "block_type": "company_enrichment", "block_id": "enrich",
         "specs": {
           "find_people": true,
           "people_focus_prompt": "VP Sales, Head of Sales, CRO, Sales Director",
           "return_fields": {
             "revenue": {"description": "Annual revenue estimate", "type": "str"},
             "employee_count": {"description": "Total employees", "type": "int"},
             "funding": {"description": "Latest funding round and amount", "type": "str"}
           }
         }},
        {"sequence_number": 3, "block_name": "company_to_leads", "block_type": "company_to_leads", "block_id": "extract_people", "specs": {}},
        {"sequence_number": 4, "block_name": "find_email", "block_type": "find_email", "block_id": "emails", "specs": {"mode": "PROFESSIONAL"}},
        {"sequence_number": 5, "block_name": "find_phone", "block_type": "find_phone", "block_id": "phones", "specs": {}},
        {"sequence_number": 6, "block_name": "append_to_notebook", "block_type": "append_to_notebook", "block_id": "save",
         "specs": {"notebook_id": "__create_new__", "notebook_name": "Sales Leaders"}}
      ],
      "edges": [
        {"from_block_id": "input", "to_block_id": "enrich"},
        {"from_block_id": "enrich", "to_block_id": "extract_people"},
        {"from_block_id": "extract_people", "to_block_id": "emails"},
        {"from_block_id": "emails", "to_block_id": "phones"},
        {"from_block_id": "phones", "to_block_id": "save"}
      ]
    }
  }'
```

Then run with company data:

```bash
curl -s -X POST "$API_URL/workflows/run?workflow_id=WF_ID" \
  -H "x-api-key: $SIXTYFOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"webhook_payload": [
    {"company_name": "Stripe", "website": "stripe.com"},
    {"company_name": "Ramp", "website": "ramp.com"},
    {"company_name": "Brex", "website": "brex.com"},
    {"company_name": "Mercury", "website": "mercury.com"},
    {"company_name": "Plaid", "website": "plaid.com"}
  ]}'
```

Note the `company_to_leads` block between `company_enrichment` and `find_email` — this is required because `find_email` operates on LEAD data, not COMPANY data.
