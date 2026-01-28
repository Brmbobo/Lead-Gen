# LEAD-GEN MASTER EXECUTION PLAN

> **Verzia:** 2.0
> **Dátum:** 2026-01-28
> **Architektúra:** Multi-Agent Parallel Execution s Iteratívnym Review
> **Stav:** IN PROGRESS

---

## EXECUTIVE SUMMARY

Tento dokument je **MASTER CONTROL FILE** pre dokončenie Lead-Gen projektu.
Každý krok je sledovateľný pomocou checkboxov. Aktuálny stav: **~55% COMPLETE**

### Legenda stavov
- `[ ]` - Čaká na vykonanie
- `[~]` - V procese
- `[x]` - Dokončené
- `[!]` - Blokované / Potrebuje pozornosť
- `[R]` - V review iterácii

---

## AKTUÁLNY STAV PROJEKTU

### Prehľad komponentov

| Komponent | Stav | Pokrok | Priorita |
|-----------|------|--------|----------|
| Backend Core | Hotový | 82% | - |
| Backend Services | Hotový | 88% | - |
| Backend Tools | Hotový | 90% | - |
| Backend Workflows | Hotový | 85% | - |
| Frontend Dashboard | Začatý | 15% | **VYSOKÁ** |
| API Integration | Nezačatý | 0% | **KRITICKÁ** |
| Testing | Nedostatočný | 39% | **KRITICKÁ** |
| Documentation | Minimálny | 20% | STREDNÁ |
| Infrastructure | Funkčný | 65% | STREDNÁ |

---

## FÁZA 1: TESTING FOUNDATION (KRITICKÁ)
**Cieľ:** Zvýšiť test coverage z 39% na 80%
**Paralelní agenti:** 2 + 1 kritik

### Sprint 1.1: Service Layer Tests
**Status:** `[ ]` NOT STARTED

#### Agent A: Backend Test Developer (Services)
```
Fokus: Hunter, OpenAI, Places, Sheets services
Target: tests/unit/test_services.py
```

- [ ] **1.1.1** Nastaviť mock fixtures pre external APIs
  - [ ] Hunter.io mock responses
  - [ ] OpenAI mock responses
  - [ ] Google Places mock responses
  - [ ] Google Sheets mock responses
- [ ] **1.1.2** Implementovať testy pre HunterService
  - [ ] test_find_email_success
  - [ ] test_find_email_not_found
  - [ ] test_verify_email
  - [ ] test_search_domain
  - [ ] test_rate_limiting
  - [ ] test_circuit_breaker
- [ ] **1.1.3** Implementovať testy pre OpenAIService
  - [ ] test_generate_message_slovak
  - [ ] test_generate_message_batch
  - [ ] test_token_counting
  - [ ] test_prompt_injection_prevention
  - [ ] test_rate_limiting
- [ ] **1.1.4** Implementovať testy pre PlacesService
  - [ ] test_search_text
  - [ ] test_get_place_details
  - [ ] test_location_bias
  - [ ] test_field_masking
- [ ] **1.1.5** Implementovať testy pre SheetsService
  - [ ] test_export_leads
  - [ ] test_create_spreadsheet
  - [ ] test_share_spreadsheet
  - [ ] test_batch_operations

#### Agent B: Backend Test Developer (Core)
```
Fokus: Secrets, Retry, GDPR modules
Target: tests/unit/test_core_extended.py
```

- [ ] **1.1.6** Implementovať testy pre secrets.py (0% → 80%)
  - [ ] test_env_secret_provider
  - [ ] test_vault_secret_provider
  - [ ] test_aws_secret_provider
  - [ ] test_secret_caching
  - [ ] test_health_check
- [ ] **1.1.7** Rozšíriť testy pre retry.py (43% → 80%)
  - [ ] test_exponential_backoff
  - [ ] test_circuit_breaker_states
  - [ ] test_half_open_recovery
- [ ] **1.1.8** Rozšíriť testy pre sanitization.py (46% → 80%)
  - [ ] test_sql_injection_patterns
  - [ ] test_xss_patterns
  - [ ] test_path_traversal
  - [ ] test_command_injection

#### Kritik C: Test Quality Reviewer
```
Iterácia 1: Kontrola pokrytia a kvality testov
Iterácia 2: Finálna validácia
```

- [ ] **1.1.9** Review Iterácia 1
  - [ ] Skontrolovať test coverage report
  - [ ] Overiť edge cases
  - [ ] Validovať mock accuracy
  - [ ] Poskytnúť feedback agentom A a B
- [ ] **1.1.10** Review Iterácia 2
  - [ ] Verifikovať opravy z Iterácie 1
  - [ ] Finálne schválenie

#### Tests Execution
- [ ] **1.1.11** Spustiť kompletný test suite
  - [ ] pytest tests/ --cov=src/lead_gen --cov-report=term-missing
  - [ ] Overiť coverage >= 80%
  - [ ] Všetky testy PASS

---

### Sprint 1.2: Workflow & CLI Tests
**Status:** `[ ]` NOT STARTED

#### Agent A: Workflow Test Developer
```
Fokus: Workflow orchestration tests
Target: tests/unit/test_workflows.py, tests/integration/test_e2e.py
```

- [ ] **1.2.1** Implementovať unit testy pre BaseWorkflow
  - [ ] test_workflow_creation
  - [ ] test_step_execution
  - [ ] test_error_handling
  - [ ] test_stop_on_error
- [ ] **1.2.2** Implementovať unit testy pre LeadGenWorkflow
  - [ ] test_scrape_step
  - [ ] test_filter_step
  - [ ] test_enrich_step
  - [ ] test_generate_step
  - [ ] test_export_step
  - [ ] test_full_pipeline_mock
- [ ] **1.2.3** Implementovať integration testy
  - [ ] test_workflow_from_yaml
  - [ ] test_partial_failure_recovery
  - [ ] test_context_propagation

#### Agent B: CLI Test Developer
```
Fokus: CLI command tests
Target: tests/unit/test_cli.py
```

- [ ] **1.2.4** Implementovať CLI testy
  - [ ] test_cli_help
  - [ ] test_cli_validate_env
  - [ ] test_cli_run_workflow
  - [ ] test_cli_list_workflows
  - [ ] test_cli_error_handling
  - [ ] test_exit_codes

#### Kritik C: Integration Reviewer
- [ ] **1.2.5** Review Iterácia 1
- [ ] **1.2.6** Review Iterácia 2

#### Tests Execution
- [ ] **1.2.7** Spustiť testy
  - [ ] Verify coverage still >= 80%
  - [ ] All tests PASS

---

## FÁZA 2: FRONTEND API INTEGRATION
**Cieľ:** Prepojiť frontend s backendom
**Paralelní agenti:** 2 + 1 kritik

### Sprint 2.1: API Client Layer
**Status:** `[ ]` NOT STARTED

#### Agent A: API Client Developer
```
Fokus: TypeScript API client
Target: frontend/lib/api/
```

- [ ] **2.1.1** Vytvoriť API client infraštruktúru
  - [ ] frontend/lib/api/client.ts (fetch wrapper)
  - [ ] frontend/lib/api/types.ts (TypeScript types)
  - [ ] frontend/lib/api/errors.ts (error handling)
- [ ] **2.1.2** Implementovať API endpoints
  - [ ] /api/leads - CRUD operations
  - [ ] /api/workflows - workflow management
  - [ ] /api/workflows/[id]/run - execute workflow
  - [ ] /api/settings - user settings
- [ ] **2.1.3** Implementovať autentifikáciu
  - [ ] API key management
  - [ ] Token storage (secure)
  - [ ] Auth context provider

#### Agent B: Backend API Developer
```
Fokus: REST API endpoints
Target: src/lead_gen/api/
```

- [ ] **2.1.4** Vytvoriť FastAPI/Flask REST endpoints
  - [ ] src/lead_gen/api/__init__.py
  - [ ] src/lead_gen/api/routes/leads.py
  - [ ] src/lead_gen/api/routes/workflows.py
  - [ ] src/lead_gen/api/routes/settings.py
  - [ ] src/lead_gen/api/middleware.py (CORS, auth)
- [ ] **2.1.5** Implementovať API dokumentáciu
  - [ ] OpenAPI/Swagger spec
  - [ ] API versioning

#### Kritik C: API Architecture Reviewer
- [ ] **2.1.6** Review Iterácia 1
  - [ ] Skontrolovať API design patterns
  - [ ] Validovať error handling
  - [ ] Overiť type safety
- [ ] **2.1.7** Review Iterácia 2
  - [ ] Finálne schválenie

#### Tests Execution
- [ ] **2.1.8** API Integration tests
  - [ ] Test all endpoints
  - [ ] Test error scenarios
  - [ ] Test authentication

---

### Sprint 2.2: State Management & Data Fetching
**Status:** `[ ]` NOT STARTED

#### Agent A: Frontend State Developer
```
Fokus: React state management
Target: frontend/lib/store/, frontend/hooks/
```

- [ ] **2.2.1** Implementovať state management
  - [ ] frontend/lib/store/index.ts (Zustand/Redux)
  - [ ] frontend/lib/store/leads.ts
  - [ ] frontend/lib/store/workflows.ts
  - [ ] frontend/lib/store/settings.ts
- [ ] **2.2.2** Implementovať data fetching hooks
  - [ ] frontend/hooks/useLeads.ts (React Query/SWR)
  - [ ] frontend/hooks/useWorkflows.ts
  - [ ] frontend/hooks/useSettings.ts
  - [ ] frontend/hooks/useAuth.ts
- [ ] **2.2.3** Implementovať real-time updates
  - [ ] WebSocket connection (optional)
  - [ ] Polling fallback

#### Agent B: Frontend Component Developer
```
Fokus: Data-connected components
Target: frontend/components/
```

- [ ] **2.2.4** Refaktorovať Dashboard s real data
  - [ ] StatsCard with API data
  - [ ] RecentActivity with API data
  - [ ] WorkflowCard with API data
- [ ] **2.2.5** Implementovať loading states
  - [ ] Skeleton loaders
  - [ ] Error boundaries
  - [ ] Retry buttons

#### Kritik C: Frontend Architecture Reviewer
- [ ] **2.2.6** Review Iterácia 1
- [ ] **2.2.7** Review Iterácia 2

#### Tests Execution
- [ ] **2.2.8** Frontend unit tests
  - [ ] Test hooks
  - [ ] Test store actions
  - [ ] Test components

---

## FÁZA 3: FRONTEND PAGES
**Cieľ:** Implementovať chýbajúce stránky
**Paralelní agenti:** 2 + 1 kritik

### Sprint 3.1: Lead Management Pages
**Status:** `[ ]` NOT STARTED

#### Agent A: Lead Pages Developer
```
Target: frontend/app/leads/
```

- [ ] **3.1.1** Implementovať Leads List Page
  - [ ] frontend/app/leads/page.tsx
  - [ ] Data table component
  - [ ] Pagination
  - [ ] Filtering & Search
  - [ ] Sorting
- [ ] **3.1.2** Implementovať Lead Detail Page
  - [ ] frontend/app/leads/[id]/page.tsx
  - [ ] Lead information display
  - [ ] Edit capabilities
  - [ ] GDPR actions (export, delete)
- [ ] **3.1.3** Implementovať Lead Export
  - [ ] CSV export
  - [ ] Excel export
  - [ ] GDPR data export

#### Agent B: Workflow Pages Developer
```
Target: frontend/app/workflows/
```

- [ ] **3.1.4** Implementovať Workflows List Page
  - [ ] frontend/app/workflows/page.tsx
  - [ ] Workflow cards/list
  - [ ] Status indicators
  - [ ] Run/Stop buttons
- [ ] **3.1.5** Implementovať Workflow Runner
  - [ ] frontend/app/workflows/[id]/page.tsx
  - [ ] Configuration form
  - [ ] Real-time progress
  - [ ] Results display
- [ ] **3.1.6** Implementovať Workflow History
  - [ ] Past executions
  - [ ] Logs viewer

#### Kritik C: UX/UI Reviewer
- [ ] **3.1.7** Review Iterácia 1
  - [ ] Responsive design check
  - [ ] Accessibility audit
  - [ ] UX flow validation
- [ ] **3.1.8** Review Iterácia 2

#### Tests Execution
- [ ] **3.1.9** E2E tests pre Lead pages
- [ ] **3.1.10** E2E tests pre Workflow pages

---

### Sprint 3.2: Settings & GDPR Pages
**Status:** `[ ]` NOT STARTED

#### Agent A: Settings Pages Developer
```
Target: frontend/app/settings/
```

- [ ] **3.2.1** Implementovať Settings Page
  - [ ] frontend/app/settings/page.tsx
  - [ ] API keys configuration
  - [ ] Preferences
  - [ ] Theme toggle
- [ ] **3.2.2** Implementovať Profile Page
  - [ ] User profile
  - [ ] Account settings

#### Agent B: GDPR Pages Developer
```
Target: frontend/app/gdpr/
```

- [ ] **3.2.3** Implementovať GDPR Center
  - [ ] frontend/app/gdpr/page.tsx
  - [ ] Data export request
  - [ ] Deletion request
  - [ ] Consent management
- [ ] **3.2.4** Implementovať Privacy Dashboard
  - [ ] Processing activities log
  - [ ] Data retention status

#### Kritik C: Compliance Reviewer
- [ ] **3.2.5** Review Iterácia 1
  - [ ] GDPR compliance check
  - [ ] Legal requirements validation
- [ ] **3.2.6** Review Iterácia 2

#### Tests Execution
- [ ] **3.2.7** Settings tests
- [ ] **3.2.8** GDPR functionality tests

---

## FÁZA 4: UI COMPONENTS & POLISH
**Cieľ:** Dokončiť UI komponenty a polish
**Paralelní agenti:** 2 + 1 kritik

### Sprint 4.1: Shared Components
**Status:** `[ ]` NOT STARTED

#### Agent A: Component Library Developer
```
Target: frontend/components/ui/
```

- [ ] **4.1.1** Implementovať základné komponenty
  - [ ] DataTable (sortable, filterable)
  - [ ] Modal/Dialog
  - [ ] Form components (Input, Select, DatePicker)
  - [ ] Toast notifications
  - [ ] Confirmation dialogs
- [ ] **4.1.2** Implementovať layout komponenty
  - [ ] Breadcrumbs
  - [ ] Page header
  - [ ] Empty states
  - [ ] Error states

#### Agent B: Form & Validation Developer
```
Target: frontend/lib/forms/
```

- [ ] **4.1.3** Implementovať form handling
  - [ ] React Hook Form setup
  - [ ] Zod validation schemas
  - [ ] Form error display
- [ ] **4.1.4** Implementovať špecifické formuláre
  - [ ] Workflow configuration form
  - [ ] API keys form
  - [ ] Lead filter form

#### Kritik C: Design System Reviewer
- [ ] **4.1.5** Review Iterácia 1
  - [ ] Component consistency
  - [ ] Design tokens usage
  - [ ] Dark mode support
- [ ] **4.1.6** Review Iterácia 2

---

### Sprint 4.2: Performance & Accessibility
**Status:** `[ ]` NOT STARTED

#### Agent A: Performance Optimizer
```
Fokus: Core Web Vitals
```

- [ ] **4.2.1** Optimalizovať performance
  - [ ] Code splitting
  - [ ] Image optimization
  - [ ] Lazy loading
  - [ ] Bundle size reduction
- [ ] **4.2.2** Merať a vylepšiť metriky
  - [ ] FCP < 1.5s
  - [ ] LCP < 2.5s
  - [ ] CLS < 0.1

#### Agent B: Accessibility Developer
```
Fokus: WCAG 2.1 AA
```

- [ ] **4.2.3** Implementovať accessibility
  - [ ] Keyboard navigation
  - [ ] Screen reader support
  - [ ] Focus management
  - [ ] ARIA labels
- [ ] **4.2.4** Accessibility audit
  - [ ] axe-core scan
  - [ ] Lighthouse a11y > 95

#### Kritik C: Quality Reviewer
- [ ] **4.2.5** Review Iterácia 1
- [ ] **4.2.6** Review Iterácia 2

#### Final Tests
- [ ] **4.2.7** Performance testing
- [ ] **4.2.8** Accessibility testing
- [ ] **4.2.9** Cross-browser testing

---

## FÁZA 5: DOCUMENTATION & DEPLOYMENT
**Cieľ:** Kompletná dokumentácia a deployment ready
**Paralelní agenti:** 2 + 1 kritik

### Sprint 5.1: Documentation
**Status:** `[ ]` NOT STARTED

#### Agent A: Technical Documentation
```
Target: docs/, README.md
```

- [ ] **5.1.1** Rozšíriť README.md
  - [ ] Project overview
  - [ ] Quick start guide
  - [ ] Configuration
  - [ ] Architecture diagram
- [ ] **5.1.2** Vytvoriť developer docs
  - [ ] docs/ARCHITECTURE.md
  - [ ] docs/API.md
  - [ ] docs/DEPLOYMENT.md
  - [ ] docs/CONTRIBUTING.md

#### Agent B: API Documentation
```
Target: API docs, examples
```

- [ ] **5.1.3** API dokumentácia
  - [ ] OpenAPI specification
  - [ ] Usage examples
  - [ ] Error codes reference
- [ ] **5.1.4** User guide
  - [ ] Getting started
  - [ ] Workflow configuration
  - [ ] Troubleshooting

#### Kritik C: Documentation Reviewer
- [ ] **5.1.5** Review Iterácia 1
- [ ] **5.1.6** Review Iterácia 2

---

### Sprint 5.2: CI/CD & Production Readiness
**Status:** `[ ]` NOT STARTED

#### Agent A: CI/CD Developer
```
Target: .github/workflows/
```

- [ ] **5.2.1** Rozšíriť CI pipeline
  - [ ] Add frontend tests to CI
  - [ ] Add E2E tests
  - [ ] Add performance benchmarks
- [ ] **5.2.2** Implementovať CD pipeline
  - [ ] .github/workflows/deploy.yml
  - [ ] Staging deployment
  - [ ] Production deployment
  - [ ] Rollback capability

#### Agent B: Infrastructure Developer
```
Target: Docker, configs
```

- [ ] **5.2.3** Finalizovať Docker setup
  - [ ] Frontend Dockerfile
  - [ ] Combined docker-compose
  - [ ] Environment configs
- [ ] **5.2.4** Production readiness
  - [ ] Health endpoints
  - [ ] Monitoring setup
  - [ ] Log aggregation

#### Kritik C: DevOps Reviewer
- [ ] **5.2.5** Review Iterácia 1
  - [ ] Security scan
  - [ ] Best practices check
- [ ] **5.2.6** Review Iterácia 2

---

## FÁZA 6: FINAL VALIDATION
**Cieľ:** Production release
**Sekvenčná validácia**

### Sprint 6.1: Final Gates
**Status:** `[ ]` NOT STARTED

- [ ] **6.1.1** Security Audit
  - [ ] Dependency vulnerability scan
  - [ ] Container security scan
  - [ ] API security review
  - [ ] OWASP Top 10 check

- [ ] **6.1.2** Performance Validation
  - [ ] Load testing
  - [ ] Stress testing
  - [ ] Memory leak check

- [ ] **6.1.3** Compliance Verification
  - [ ] GDPR compliance checklist
  - [ ] Privacy policy review
  - [ ] Data handling audit

- [ ] **6.1.4** Documentation Complete
  - [ ] All docs reviewed
  - [ ] Examples working
  - [ ] README complete

- [ ] **6.1.5** Test Coverage
  - [ ] Backend >= 80%
  - [ ] Frontend >= 70%
  - [ ] E2E tests passing

- [ ] **6.1.6** Production Deployment
  - [ ] Staging verified
  - [ ] Production deployed
  - [ ] Smoke tests passing

---

## PROGRESS TRACKING

### Celkový Progress

```
FÁZA 1: Testing Foundation    [░░░░░░░░░░] 0%
FÁZA 2: API Integration       [░░░░░░░░░░] 0%
FÁZA 3: Frontend Pages        [░░░░░░░░░░] 0%
FÁZA 4: UI Components         [░░░░░░░░░░] 0%
FÁZA 5: Documentation         [░░░░░░░░░░] 0%
FÁZA 6: Final Validation      [░░░░░░░░░░] 0%
─────────────────────────────────────────────
CELKOVO:                      [░░░░░░░░░░] 0%
```

### Časová os

| Fáza | Sprint | Status | Začiatok | Koniec |
|------|--------|--------|----------|--------|
| 1 | 1.1 | `[ ]` | - | - |
| 1 | 1.2 | `[ ]` | - | - |
| 2 | 2.1 | `[ ]` | - | - |
| 2 | 2.2 | `[ ]` | - | - |
| 3 | 3.1 | `[ ]` | - | - |
| 3 | 3.2 | `[ ]` | - | - |
| 4 | 4.1 | `[ ]` | - | - |
| 4 | 4.2 | `[ ]` | - | - |
| 5 | 5.1 | `[ ]` | - | - |
| 5 | 5.2 | `[ ]` | - | - |
| 6 | 6.1 | `[ ]` | - | - |

---

## AGENT EXECUTION LOG

### Aktívne agenti
| Agent ID | Typ | Sprint | Úloha | Status |
|----------|-----|--------|-------|--------|
| - | - | - | - | - |

### Dokončené iterácie
| Sprint | Agent A | Agent B | Kritik | Iterácie | Výsledok |
|--------|---------|---------|--------|----------|----------|
| - | - | - | - | - | - |

---

## POZNÁMKY A ROZHODNUTIA

### Rozhodnutia
- [ ] Vybrať state management (Zustand vs Redux)
- [ ] Vybrať data fetching library (React Query vs SWR)
- [ ] Rozhodnúť o API framework (FastAPI vs Flask)

### Bloky a riziká
| Riziko | Pravdepodobnosť | Dopad | Mitigácia |
|--------|-----------------|-------|-----------|
| External API changes | Stredná | Vysoký | VCR cassettes, mock layer |
| GDPR non-compliance | Nízka | Kritický | Legal review |
| Performance issues | Stredná | Stredný | Early benchmarking |

---

## PRÍLOHY

### A: Agent Responsibility Matrix

| Agent Typ | Primárne úlohy | Sekundárne úlohy |
|-----------|---------------|------------------|
| Backend Test Dev | Unit tests, Integration tests | Fixtures |
| Frontend Dev | Components, Pages | Hooks |
| API Dev | Endpoints, Auth | Documentation |
| Kritik | Review, Validation | Architecture |

### B: Review Checklist Template

```markdown
## Review Checklist - Sprint X.X

### Kód
- [ ] Type safety
- [ ] Error handling
- [ ] No hardcoded values
- [ ] Logging

### Testy
- [ ] Coverage >= target
- [ ] Edge cases
- [ ] Mocks accurate

### Dokumentácia
- [ ] JSDoc/docstrings
- [ ] README updated

### Bezpečnosť
- [ ] No secrets exposed
- [ ] Input validation
- [ ] GDPR compliant
```

---

*Posledná aktualizácia: 2026-01-28*
*Zodpovedný: Claude Opus 4.5 Orchestrator*
