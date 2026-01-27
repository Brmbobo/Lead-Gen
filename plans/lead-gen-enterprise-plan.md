# Lead Generation Application - Enterprise Implementation Plan

## Overview
Build an enterprise-grade lead generation application that scrapes business leads (dentists/zubári) from Google Places API, generates personalized AI outreach messages in **Slovak language** using OpenAI GPT-4o-mini, enriches with Hunter.io emails, and exports to Google Sheets.

## Target Market
- **Primary**: Dentists (zubári) in Slovakia
- **Future expansion**: Austria (Zahnarzt), Czech Republic (zubař)
- **Agency**: UpAI - Custom AI consulting and implementation

## User Preferences (Confirmed)
- **LLM Model**: GPT-4o-mini ($0.15/$0.60 per 1M tokens)
- **Language**: Slovak (Slovenčina)
- **Email Enrichment**: Hunter.io + manual research column
- **Deployment**: Docker container
- **Business Type**: Dentists (zubári, zubný lekár)

## Tech Stack (Latest Versions via Context7)

| Component | Library | Version | Purpose |
|-----------|---------|---------|---------|
| Data Validation | `pydantic` | v2.5+ | Models, validation, settings |
| Settings | `pydantic-settings` | v2.1+ | Environment config with nested models |
| AI Generation | `openai` | v1.6+ | Async chat completions |
| Google Places | `google-api-python-client` | latest | Places API v1 (New) |
| Google Sheets | `gspread` | v6.0+ | Spreadsheet operations |
| Async HTTP | `aiohttp` | v3.9+ | Rate-limited API calls |
| CLI | `click` | v8.1+ | Command-line interface |
| Deployment | `modal` | latest | Serverless cron jobs |
| Email Enrichment | `hunter-io` / `apollo` | latest | Optional email finder |

---

## LLM Model Comparison (January 2026)

Based on [IntuitionLabs](https://intuitionlabs.ai/articles/llm-api-pricing-comparison-2025) and [CloudIDR](https://www.cloudidr.com/blog/llm-pricing-comparison-2026) research:

| Model | Input (per 1M) | Output (per 1M) | Context | Best For |
|-------|----------------|-----------------|---------|----------|
| **GPT-4o** | $2.50 | $10.00 | 128K | Best all-rounder |
| **GPT-4o-mini** | $0.15 | $0.60 | 128K | Cost-effective production |
| **Claude 3.7 Sonnet** | $3.00 | $15.00 | 200K | Long context, safety |
| **Claude Opus 4.1** | $15.00 | $75.00 | 200K | Complex reasoning |
| **Gemini 2.5 Pro** | $2.50 | $15.00 | 1M | Massive context |
| **Gemini 2.5 Flash** | $0.15 | $0.60 | 1M | Budget + huge context |
| **DeepSeek V3** | $0.27 | $1.10 | 64K | Budget option |

**Recommendation for Lead Gen:** `GPT-4o-mini` or `Gemini 2.5 Flash` for outreach generation (70-80% of tasks perform identically to premium models at 1/10th cost).

---

## Google Places API (New) Pricing

Based on [Google Places API docs](https://developers.google.com/maps/documentation/places/web-service/usage-and-billing):

| SKU Tier | Fields Included | Cost per 1K requests |
|----------|-----------------|---------------------|
| **IDs Only** | place_id only | $0.00 |
| **Location** | + geometry | $5.00 |
| **Basic** | + name, address, types | $17.00 |
| **Advanced** | + phone, website, hours | $20.00 |
| **Preferred** | + reviews, photos | $35.00 |

**Cost Optimization:**
- Use `FieldMask` header to request ONLY needed fields
- $200/month free credit available
- Text Search (New) costs more than Place Details (New) - get place_id first, then fetch details

---

## Email Enrichment Options (Optional Enhancement)

Based on [Lobstr comparison](https://www.lobstr.io/blog/email-finder-api) and [Apollo docs](https://docs.apollo.io/reference/people-enrichment):

| Provider | Accuracy | Speed | Free Tier | Best For |
|----------|----------|-------|-----------|----------|
| **Hunter.io** | ~95% deliverability | Moderate | Permanent free | Email-focused, simple |
| **Apollo.io** | ~91% accuracy | Fastest (1000 in 8 min) | 100 credits/mo | All-in-one sales |
| **Findymail** | <2% bounce rate | Moderate | Limited | Maximum quality |

**API Integration Example:**
```python
# Hunter.io - Find email by domain
# GET https://api.hunter.io/v2/domain-search?domain=example.com&api_key=xxx

# Apollo.io - People enrichment
# POST https://api.apollo.io/v1/people/match
# Body: {"first_name": "John", "last_name": "Doe", "organization_name": "Acme"}
```

---

## Project Structure

```
Lead-Gen/
├── .env                          # API keys (git-ignored)
├── .env.example                  # Template
├── pyproject.toml                # Dependencies & config
├── CLAUDE.md                     # AI context
│
├── src/lead_gen/
│   ├── __init__.py
│   ├── __main__.py               # Entry: python -m lead_gen
│   ├── cli.py                    # Click CLI
│   │
│   ├── core/                     # Infrastructure
│   │   ├── config.py             # Pydantic Settings
│   │   ├── exceptions.py         # Error hierarchy
│   │   ├── rate_limiter.py       # Token bucket
│   │   └── retry.py              # Exponential backoff
│   │
│   ├── models/                   # Domain models
│   │   ├── lead.py               # Lead, EnrichedLead
│   │   ├── outreach.py           # OutreachMessage
│   │   └── workflow.py           # WorkflowConfig
│   │
│   ├── tools/                    # Modular tools
│   │   ├── base.py               # BaseTool abstract class
│   │   ├── scrape_leads.py       # Google Places scraper
│   │   ├── generate_outreach.py  # OpenAI message gen
│   │   └── export_to_sheets.py   # Google Sheets export
│   │
│   ├── services/                 # API wrappers
│   │   ├── places_service.py     # Places API v1 client
│   │   ├── openai_service.py     # OpenAI async client
│   │   └── sheets_service.py     # gspread wrapper
│   │
│   └── workflows/                # Orchestration
│       ├── base.py               # BaseWorkflow
│       └── lead_generation.py    # Main workflow
│
├── workflows/                    # YAML configs
│   └── dentist_leads.yaml
│
├── tests/
│   ├── unit/
│   └── integration/
│
└── deploy/
    └── modal_app.py              # Serverless deployment
```

---

## Implementation Phases

### Phase 1: Core Infrastructure

**Files to create:**
- `src/lead_gen/core/config.py`
- `src/lead_gen/core/exceptions.py`
- `src/lead_gen/core/rate_limiter.py`
- `src/lead_gen/core/retry.py`

**Key patterns (from Context7 docs):**

```python
# config.py - Pydantic Settings with nested models
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class GooglePlacesConfig(BaseSettings):
    api_key: SecretStr
    requests_per_minute: int = 60

    model_config = SettingsConfigDict(
        env_prefix="GOOGLE_PLACES_",
        env_file=".env"
    )

class OpenAIConfig(BaseSettings):
    api_key: SecretStr
    model: str = "gpt-4o"

    model_config = SettingsConfigDict(
        env_prefix="OPENAI_",
        env_file=".env"
    )

class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter='__')

    google_places: GooglePlacesConfig
    openai: OpenAIConfig
```

---

### Phase 2: Domain Models

**Files to create:**
- `src/lead_gen/models/lead.py`
- `src/lead_gen/models/outreach.py`
- `src/lead_gen/models/workflow.py`

**Key models:**

```python
# lead.py
from pydantic import BaseModel, Field, HttpUrl
from enum import Enum

class LeadStatus(str, Enum):
    NEW = "new"
    ENRICHED = "enriched"
    CONTACTED = "contacted"

class Lead(BaseModel):
    id: str
    name: str
    business_type: str
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    website: HttpUrl | None = None
    rating: float | None = Field(None, ge=0, le=5)
    review_count: int | None = Field(None, ge=0)
    google_maps_url: HttpUrl | None = None
```

---

### Phase 3: API Services

**Files to create:**
- `src/lead_gen/services/places_service.py`
- `src/lead_gen/services/openai_service.py`
- `src/lead_gen/services/sheets_service.py`

**Google Places API v1 (New API - from Context7):**

```python
# places_service.py - Using Places API v1 (searchText)
import aiohttp

class PlacesService:
    BASE_URL = "https://places.googleapis.com/v1/places:searchText"

    async def search_text(self, query: str, location: dict, radius: int = 50000):
        headers = {
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,"
                               "places.nationalPhoneNumber,places.websiteUri,"
                               "places.rating,places.userRatingCount,places.googleMapsUri"
        }
        payload = {
            "textQuery": query,
            "locationBias": {
                "circle": {
                    "center": {"latitude": location["lat"], "longitude": location["lng"]},
                    "radius": radius
                }
            },
            "maxResultCount": 20
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(self.BASE_URL, json=payload, headers=headers) as resp:
                return await resp.json()
```

**OpenAI Async - Slovak Language (from Context7):**

```python
# openai_service.py
from openai import AsyncOpenAI, APIError, RateLimitError, AuthenticationError

class OpenAIService:
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    async def generate_outreach(self, lead: Lead, tone: str, language: str = "sk") -> str:
        system_prompt = """Si profesionálny obchodný copywriter pre UpAI, agentúru
        poskytujúcu AI automatizáciu a konzultácie. Píš personalizované oslovovacie
        správy v slovenčine.

        Pravidlá:
        - Spomeň konkrétne detaily o firme (hodnotenie, počet recenzií, lokalitu)
        - Ponúkni hodnotu: AI automatizácia pre zubné ambulancie
        - Buď profesionálny ale priateľský
        - Max 150 slov
        - Zakonči výzvou k akcii (krátky hovor/stretnutie)"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",  # Cost-effective for outreach
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": self._build_lead_prompt_sk(lead)}
                ],
                max_tokens=400,
                temperature=0.7
            )
            return response.choices[0].message.content
        except RateLimitError:
            raise  # Handled by retry decorator
        except AuthenticationError:
            raise ConfigurationError("Invalid OpenAI API key")

    def _build_lead_prompt_sk(self, lead: Lead) -> str:
        return f"""Vytvor oslovovaciu správu pre túto zubnú ambulanciu:

- Názov: {lead.name}
- Mesto: {lead.city}
- Hodnotenie: {lead.rating}/5 ({lead.review_count} recenzií)
- Web: {lead.website or 'nemá'}

Naša ponuka: AI automatizácia pre zubné ambulancie - online rezervácie,
pripomienky pacientom, automatické odpovede na otázky."""
```

**Google Sheets with gspread (from Context7):**

```python
# sheets_service.py
import gspread
import json
import os

class SheetsService:
    def __init__(self):
        # Support both file and env var auth
        if os.environ.get("GOOGLE_SERVICE_ACCOUNT"):
            creds = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT"])
            self.gc = gspread.service_account_from_dict(creds)
        else:
            self.gc = gspread.service_account(filename="service_account.json")

    def export_leads(self, leads: list[Lead], spreadsheet_name: str):
        sh = self.gc.create(spreadsheet_name)
        sh.share("user@example.com", perm_type="user", role="writer")

        worksheet = sh.sheet1
        headers = ["Name", "Phone", "Address", "City", "Rating", "Reviews", "Website", "Message"]
        data = [headers] + [self._lead_to_row(l) for l in leads]

        worksheet.update(data, "A1")
        return sh.url
```

---

### Phase 4: Tools Layer

**Files to create:**
- `src/lead_gen/tools/base.py`
- `src/lead_gen/tools/scrape_leads.py`
- `src/lead_gen/tools/generate_outreach.py`
- `src/lead_gen/tools/export_to_sheets.py`

**Pattern:**

```python
# base.py
from abc import ABC, abstractmethod
from pydantic import BaseModel

class BaseTool(ABC):
    name: str

    @abstractmethod
    async def execute(self, input_data: BaseModel) -> BaseModel:
        pass
```

---

### Phase 5: Workflow Orchestration

**Files to create:**
- `src/lead_gen/workflows/base.py`
- `src/lead_gen/workflows/lead_generation.py`
- `workflows/dentist_leads.yaml`

**Workflow config (YAML):**

```yaml
# workflows/slovakia_dentists.yaml
id: slovakia_zubari
name: "Zubári na Slovensku"

business_types:
  - "zubár"
  - "zubný lekár"
  - "zubná ambulancia"
  - "dentist"

locations:
  - query: "Bratislava, Slovakia"
    lat: 48.1486
    lng: 17.1077
    radius_meters: 30000
  - query: "Košice, Slovakia"
    lat: 48.7164
    lng: 21.2611
    radius_meters: 25000
  - query: "Žilina, Slovakia"
    lat: 49.2231
    lng: 18.7394
    radius_meters: 20000
  - query: "Banská Bystrica, Slovakia"
    lat: 48.7360
    lng: 19.1461
    radius_meters: 20000

language: sk  # Slovak
outreach_tone: professional

# Email enrichment
email_enrichment:
  provider: hunter
  fallback: manual_column  # Add empty column for manual lookup

export:
  format: google_sheets
  sheet_name: "Zubári SK - Leads"
  columns:
    - name
    - phone
    - address
    - city
    - website
    - rating
    - reviews
    - email_hunter      # From Hunter.io
    - email_manual      # For manual research
    - outreach_message  # AI-generated in Slovak
    - status            # New/Contacted/Responded

filters:
  min_rating: 4.0
  min_reviews: 5
  require_phone: true
```

---

### Phase 6: CLI Interface

**File:** `src/lead_gen/cli.py`

```python
import click
import asyncio

@click.group()
def cli():
    """Lead Generation CLI"""
    pass

@cli.command()
@click.argument("workflow_file")
@click.option("--dry-run", is_flag=True)
def run(workflow_file: str, dry_run: bool):
    """Run a workflow from YAML config"""
    asyncio.run(execute_workflow(workflow_file, dry_run))

@cli.command()
def validate_env():
    """Check API keys are configured"""
    pass
```

---

### Phase 7: Docker Deployment

**Files to create:**
- `Dockerfile`
- `docker-compose.yml`
- `.dockerignore`

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

# Copy source
COPY src/ ./src/
COPY workflows/ ./workflows/

# Set environment
ENV PYTHONUNBUFFERED=1

# Entry point
ENTRYPOINT ["python", "-m", "lead_gen"]
CMD ["--help"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  lead-gen:
    build: .
    env_file:
      - .env
    volumes:
      - ./workflows:/app/workflows:ro
      - ./output:/app/output
    command: ["run", "workflows/slovakia_dentists.yaml"]

  # Optional: scheduled runs with cron
  lead-gen-cron:
    build: .
    env_file:
      - .env
    volumes:
      - ./workflows:/app/workflows:ro
      - ./output:/app/output
    entrypoint: ["/bin/sh", "-c"]
    command: |
      echo "0 8 * * 1 python -m lead_gen run /app/workflows/slovakia_dentists.yaml" | crontab -
      crond -f
```

**Run commands:**
```bash
# Build container
docker build -t lead-gen .

# Run single workflow
docker run --env-file .env lead-gen run workflows/slovakia_dentists.yaml

# Run with docker-compose
docker-compose up lead-gen
```

---

### Phase 8: Hunter.io Email Enrichment

**File:** `src/lead_gen/services/hunter_service.py`

```python
import aiohttp
from typing import Optional

class HunterService:
    """Hunter.io email finder for EU markets."""

    BASE_URL = "https://api.hunter.io/v2"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def find_email_by_domain(self, domain: str) -> Optional[dict]:
        """Find emails associated with a domain."""
        url = f"{self.BASE_URL}/domain-search"
        params = {
            "domain": domain,
            "api_key": self.api_key,
            "limit": 5
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    emails = data.get("data", {}).get("emails", [])
                    if emails:
                        # Return first verified email
                        for email in emails:
                            if email.get("verification", {}).get("status") == "valid":
                                return {
                                    "email": email["value"],
                                    "confidence": email.get("confidence", 0),
                                    "type": email.get("type")
                                }
                        # Fallback to first email
                        return {"email": emails[0]["value"], "confidence": emails[0].get("confidence", 0)}
                return None

    async def verify_email(self, email: str) -> dict:
        """Verify if an email is deliverable."""
        url = f"{self.BASE_URL}/email-verifier"
        params = {"email": email, "api_key": self.api_key}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                data = await resp.json()
                return {
                    "email": email,
                    "status": data.get("data", {}).get("status"),
                    "score": data.get("data", {}).get("score")
                }
```

---

## API Keys Required

| Service | Env Variable | How to Get |
|---------|-------------|------------|
| Google Places | `GOOGLE_PLACES_API_KEY` | Google Cloud Console > APIs > Places API (New) |
| OpenAI | `OPENAI_API_KEY` | platform.openai.com/api-keys |
| Google Sheets | `GOOGLE_SERVICE_ACCOUNT` | GCP > IAM > Service Accounts > JSON key |
| Hunter.io | `HUNTER_API_KEY` | hunter.io/api-keys (free tier: 25 searches/mo) |

**`.env.example`:**
```bash
# Google APIs
GOOGLE_PLACES_API_KEY=your_places_api_key
GOOGLE_SERVICE_ACCOUNT={"type":"service_account",...}

# OpenAI
OPENAI_API_KEY=sk-...

# Hunter.io (optional email enrichment)
HUNTER_API_KEY=your_hunter_key

# App Settings
LEADGEN_ENV=production
LEADGEN_LOG_LEVEL=INFO
LEADGEN_DEFAULT_LANGUAGE=sk
```

---

## Dependencies (pyproject.toml)

```toml
[project]
name = "lead-gen"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "aiohttp>=3.9.0",
    "openai>=1.6.0",
    "gspread>=6.0.0",
    "google-auth>=2.25.0",
    "click>=8.1.0",
    "pyyaml>=6.0.1",
    "python-dotenv>=1.0.0",
    "structlog>=23.2.0",
]

[project.optional-dependencies]
dev = ["pytest>=7.4.0", "pytest-asyncio>=0.23.0", "mypy>=1.7.0", "ruff>=0.1.0"]
deploy = ["modal>=0.56.0"]

[project.scripts]
lead-gen = "lead_gen.cli:cli"
```

---

## Verification Plan

1. **Unit Tests**
   - Test rate limiter token bucket logic
   - Test Pydantic models validation
   - Test retry decorator with mocked failures
   - Test Slovak message generation prompts

2. **Integration Tests**
   - Test Google Places API with "zubár Bratislava" query
   - Test OpenAI Slovak outreach generation
   - Test Hunter.io email lookup for Slovak domains (.sk)
   - Test gspread export to test spreadsheet

3. **End-to-End Test**
   ```bash
   # Validate environment
   lead-gen validate-env

   # Dry run workflow
   lead-gen run workflows/slovakia_dentists.yaml --dry-run

   # Execute with 5 leads (Bratislava only)
   lead-gen run workflows/slovakia_dentists.yaml --limit 5 --location "Bratislava"

   # Docker test
   docker run --env-file .env lead-gen run workflows/slovakia_dentists.yaml --limit 5
   ```

4. **Manual Verification**
   - Check Google Sheet has columns: name, phone, address, city, website, rating, reviews, email_hunter, email_manual, outreach_message, status
   - Verify Slovak outreach messages mention: hodnotenie (rating), recenzie (reviews), mesto (city)
   - Confirm Hunter.io finds emails for .sk domains
   - Test empty email_manual column is ready for manual research

---

## Implementation Order

1. `pyproject.toml` + `.env.example` + `.dockerignore`
2. `src/lead_gen/core/` (config, exceptions, rate_limiter, retry)
3. `src/lead_gen/models/` (lead, outreach, workflow)
4. `src/lead_gen/services/` (places, openai, sheets, hunter)
5. `src/lead_gen/tools/` (base, scrape, outreach, export, enrich_email)
6. `src/lead_gen/workflows/` (base, lead_generation)
7. `src/lead_gen/cli.py`
8. `workflows/slovakia_dentists.yaml`
9. `Dockerfile` + `docker-compose.yml`
10. `tests/`

---

## Key Design Decisions

1. **Places API v1 (New)** - Uses POST-based searchText instead of legacy GET endpoints
2. **GPT-4o-mini** - Cost-effective ($0.15/$0.60 per 1M tokens) for Slovak outreach
3. **Slovak language prompts** - System prompts in Slovak for native-quality messages
4. **Hunter.io + manual column** - Hybrid email enrichment (API + manual research)
5. **Docker deployment** - Containerized for any cloud/local environment
6. **Token bucket rate limiting** - Prevents API quota exhaustion
7. **Pydantic v2 Settings** - Type-safe config with nested env var support
8. **gspread over raw API** - Simpler auth and batch operations
9. **YAML workflows** - User-configurable without code changes
10. **Multi-city support** - Bratislava, Košice, Žilina, Banská Bystrica

---

## Estimated Costs (100 leads)

| Service | Usage | Cost |
|---------|-------|------|
| Google Places | ~200 API calls (search + details) | ~$4.00 |
| OpenAI GPT-4o-mini | ~50K tokens | ~$0.05 |
| Hunter.io | 100 domain searches | Free tier (25/mo) or $49/mo |
| Google Sheets | Unlimited | Free |
| **Total** | | **~$4-5 per 100 leads** |

---

## Future Enhancements

1. **Austria expansion**: Add "Zahnarzt Wien/Graz/Salzburg" workflows
2. **Czech expansion**: Add "zubař Praha/Brno" workflows
3. **WhatsApp integration**: Direct messaging for higher response rates
4. **CRM export**: HubSpot, Pipedrive integration
5. **Response tracking**: Track opened/replied status in sheet
