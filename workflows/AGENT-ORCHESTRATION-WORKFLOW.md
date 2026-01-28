# Lead-Gen Enterprise Agent Orchestration Workflow

> **Verzia:** 1.0
> **Dátum:** 2026-01-28
> **Architektúra:** Multi-Agent Swarm s Iteratívnym Review

---

## EXECUTIVE SUMMARY

Tento dokument definuje kompletný workflow na realizáciu Lead-Gen enterprise plánu pomocou inteligentného systému 47+ špecializovaných agentov organizovaných do 8 tímov. Každá fáza obsahuje minimálne jednu iteráciu code review s povinným schválením pred pokračovaním.

---

## INVENTÁR DOSTUPNÝCH AGENTOV

### Kategória 1: HIVE-MIND (Kolektívna Inteligencia)
| Agent | Súbor | Špecializácia | Použitie |
|-------|-------|---------------|----------|
| Queen Coordinator V3 | `hive-mind/queen-coordinator.md` | Orchestrácia 15-agentového roja | **PRIMÁRNY ORCHESTRÁTOR** |
| Scout Explorer | `hive-mind/scout-explorer.md` | Prieskum a mapovanie codebase | Analýza, discovery |
| Worker Specialist | `hive-mind/worker-specialist.md` | Exekúcia špecifických úloh | Implementácia |
| Swarm Memory Manager | `hive-mind/swarm-memory-manager.md` | Zdieľaná pamäť medzi agentmi | Koordinácia stavu |
| Collective Intelligence | `hive-mind/collective-intelligence-coordinator.md` | Fúzia multi-agentnej inteligencie | Rozhodovanie |

### Kategória 2: GOAL-ORIENTED ACTION PLANNING (GOAP)
| Agent | Súbor | Špecializácia | Použitie |
|-------|-------|---------------|----------|
| Master GOAP Orchestrator | `goal/agent.md` (51KB) | Sublineárna optimalizácia, A* plánovanie | **STRATEGICKÉ PLÁNOVANIE** |
| Goal Planner | `goal/goal-planner.md` (18KB) | Dynamická dekompozícia cieľov | Rozklad úloh |
| Code Goal Planner | `goal/code-goal-planner.md` (26KB) | Kód-špecifické plánovanie | Dev plánovanie |

### Kategória 3: ARCHITECTURE & SYSTEM DESIGN
| Agent | Súbor | Špecializácia | Použitie |
|-------|-------|---------------|----------|
| Arch System Design | `architecture-system-design/arch-system-design.md` | Architektonické rozhodnutia | Návrh systému |
| Integration Architect | `architecture-system-design/integration-architect.md` | Integračné vzory | API design |
| Security Architect | `architecture-system-design/security-architect.md` | Bezpečnostná architektúra | **GDPR, Secrets** |

### Kategória 4: CODE ANALYSIS & REVIEW
| Agent | Súbor | Špecializácia | Použitie |
|-------|-------|---------------|----------|
| Code Analyzer | `analysis/code-analyzer.md` | Komplexná analýza kódu | Kvalita kódu |
| Code Quality Analyzer | `analysis/analyze-code-quality.md` | Metriky kvality | Audit |
| Database Specialist | `analysis/database-specialist.yaml` | Databázový dizajn | Perzistencia |
| **Code Reviewer** | `code-reviewer/code-reviewer.md` | Profesionálny code review | **POVINNÝ REVIEW** |

### Kategória 5: TESTING & VALIDATION
| Agent | Súbor | Špecializácia | Použitie |
|-------|-------|---------------|----------|
| Production Validator | `testing/production-validator.md` (23KB) | Validácia production readiness | **GATE KEEPER** |
| TDD London Swarm | `testing/tdd-london-swarm.md` (14KB) | Test-Driven Development | Testing |
| Test Architect | `testing/test-architect.yaml` | Testovacia architektúra | Test design |

### Kategória 6: OPTIMIZATION & PERFORMANCE
| Agent | Súbor | Špecializácia | Použitie |
|-------|-------|---------------|----------|
| Performance Engineer V2 | `optimization/performance-engineer_v2.md` | Optimalizácia výkonu | Performance |
| Memory Specialist V2 | `optimization/memory-specialist_v2.md` | Správa pamäte | Memory leaks |
| Performance Monitor | `optimization/performance-monitor.md` | Kontinuálny monitoring | Observability |
| Resource Allocator | `optimization/resource-allocator.md` | Distribúcia zdrojov | Scaling |
| Topology Optimizer | `optimization/topology-optimizer.md` | Optimalizácia topológie | Infrastructure |
| Load Balancer | `optimization/load-balancer.md` | Rozloženie záťaže | HA |
| Benchmark Suite | `optimization/benchmark-suite.md` | Benchmarking | Baseline |

### Kategória 7: FRONTEND & DESIGN
| Agent | Súbor | Špecializácia | Použitie |
|-------|-------|---------------|----------|
| Enterprise Design System | `enterprise-frontend-design/SKILL.md` (48KB) | Komplexný design systém | **UI/UX** |
| Accessibility Agent | `enterprise-frontend-design/accessibility/` | A11y compliance | WCAG |
| Animation Agent | `enterprise-frontend-design/animation/` | Motion design | UX |
| Design Iterator | `enterprise-frontend-design/design-iterator/` | Iteratívny dizajn | Refinement |
| Design System Agent | `enterprise-frontend-design/design-system/` | Komponentová knižnica | Components |
| Enterprise Patterns | `enterprise-frontend-design/enterprise-patterns/` | B2B vzory | Enterprise UX |
| Performance Agent | `enterprise-frontend-design/performance/` | Frontend performance | FCP, LCP |

### Kategória 8: SPECIALIZED SKILLS (Business & Product)
| Skill | Súbor | Špecializácia |
|-------|-------|---------------|
| Project Manager | `08-business-product/project-manager.md` | PM praktiky |
| Scrum Master | `08-business-product/scrum-master.md` | Agile metodológia |
| Technical Writer | `08-business-product/technical-writer.md` | Dokumentácia |
| Business Analyst | `08-business-product/business-analyst.md` | Business requirements |
| Legal Advisor | `08-business-product/legal-advisor.md` | **GDPR compliance** |
| UX Researcher | `08-business-product/ux-researcher.md` | User research |

### Kategória 9: ORCHESTRATION & AUTOMATION
| Agent/Skill | Súbor | Špecializácia |
|-------------|-------|---------------|
| Maestro Workflow | `skills/maestro-workflow/` | 5-stage LLM orchestrácia |
| Dispatching Parallel | `skills/dispatching-parallel-agents/` | Multi-agent koordinácia |
| Meta Orchestration | `skills/09-meta-orchestration/` | Meta-level orchestrácia |
| n8n Workflow Architect | `skills/n8n-workflow-architect/` | Automatizačná architektúra |

### Kategória 10: DEBUGGING & MAINTENANCE
| Agent | Súbor | Špecializácia |
|-------|-------|---------------|
| Debugger | `debugger/debugger.md` | Debugging specialist |
| Project Coordinator | `project coordinator/project-coordinator.yaml` | Koordinácia projektu |

---

## VYBRANÍ OPTIMÁLNI AGENTI PRE LEAD-GEN

Na základe analýzy plánov a kritických požiadaviek vyberáme **15 kľúčových agentov**:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    LEAD-GEN AGENT DREAM TEAM                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  TIER 1: ORCHESTRATION (Bežia Paralelne)                           │
│  ╔═══════════════════════╗    ╔═══════════════════════╗            │
│  ║ Queen Coordinator V3  ║ ←→ ║ Master GOAP Agent     ║            │
│  ║ (Swarm Orchestration) ║    ║ (Strategic Planning)  ║            │
│  ╚═══════════════════════╝    ╚═══════════════════════╝            │
│           ↓                              ↓                          │
│  TIER 2: SECURITY & COMPLIANCE                                      │
│  ╔═══════════════════════╗    ╔═══════════════════════╗            │
│  ║ Security Architect    ║    ║ Legal Advisor         ║            │
│  ║ (Vault, Secrets)      ║    ║ (GDPR Compliance)     ║            │
│  ╚═══════════════════════╝    ╚═══════════════════════╝            │
│           ↓                              ↓                          │
│  TIER 3: DEVELOPMENT (Bežia Paralelne)                              │
│  ╔═══════════════╗ ╔═══════════════╗ ╔═══════════════╗             │
│  ║ Integration   ║ ║ Worker        ║ ║ Code Goal     ║             │
│  ║ Architect     ║ ║ Specialist    ║ ║ Planner       ║             │
│  ║ (API Design)  ║ ║ (Backend)     ║ ║ (Dev Tasks)   ║             │
│  ╚═══════════════╝ ╚═══════════════╝ ╚═══════════════╝             │
│           ↓               ↓               ↓                         │
│  TIER 4: QUALITY GATES (Sekvenčne)                                  │
│  ╔═══════════════╗ ╔═══════════════╗ ╔═══════════════╗             │
│  ║ Code Reviewer ║→║ Code Analyzer ║→║ Production    ║             │
│  ║ (Manual Rev)  ║ ║ (Auto Check)  ║ ║ Validator     ║             │
│  ╚═══════════════╝ ╚═══════════════╝ ╚═══════════════╝             │
│           ↓                                                         │
│  TIER 5: TESTING & OPTIMIZATION                                     │
│  ╔═══════════════╗ ╔═══════════════╗ ╔═══════════════╗             │
│  ║ TDD London    ║ ║ Performance   ║ ║ Benchmark     ║             │
│  ║ Swarm         ║ ║ Engineer V2   ║ ║ Suite         ║             │
│  ╚═══════════════╝ ╚═══════════════╝ ╚═══════════════╝             │
│           ↓                                                         │
│  TIER 6: FRONTEND (Paralelne s Backend)                             │
│  ╔═══════════════╗ ╔═══════════════╗ ╔═══════════════╗             │
│  ║ Enterprise    ║ ║ Accessibility ║ ║ Design        ║             │
│  ║ Design System ║ ║ Agent         ║ ║ Iterator      ║             │
│  ╚═══════════════╝ ╚═══════════════╝ ╚═══════════════╝             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## KOMPLETNÝ REALIZAČNÝ WORKFLOW

### FÁZA 0: INICIALIZÁCIA A LEGAL REVIEW
**Trvanie:** Pred začiatkom developmentu
**Paralelné agenty:** 2

```yaml
agents_deployed:
  - Legal Advisor:
      tasks:
        - GDPR compliance audit
        - Google Places ToS review
        - Legitimate Interest Assessment
        - Privacy Policy draft (SK/CZ/AT)
      output: /docs/legal/gdpr-compliance-report.md

  - Security Architect:
      tasks:
        - Secrets management architecture (AWS Secrets Manager/Vault)
        - Threat model
        - Security requirements specification
      output: /docs/security/threat-model.md

gate_keeper: Production Validator
review_required: true
min_iterations: 1
approval_criteria:
  - Legal compliance verified
  - Threat model approved
  - GDPR implementation plan ready
```

---

### FÁZA 1: CORE INFRASTRUCTURE (Backend)
**Paralelné agenty:** 3

```yaml
stage: core_infrastructure
parallel_execution: true

agents_deployed:
  # AGENT PAIR 1: Architecture
  - agent: Integration Architect
    focus: API design & service contracts
    deliverables:
      - src/lead_gen/core/config.py (Pydantic Settings)
      - src/lead_gen/core/exceptions.py (Error hierarchy)
      - src/lead_gen/core/rate_limiter.py (Token bucket)
      - src/lead_gen/core/retry.py (Circuit breaker)

  # AGENT PAIR 2: Security Implementation
  - agent: Security Architect
    focus: Security infrastructure
    deliverables:
      - src/lead_gen/core/secrets.py (Vault integration)
      - src/lead_gen/core/gdpr.py (Data protection layer)
      - src/lead_gen/core/sanitization.py (Input validation)

  # AGENT PAIR 3: Worker Implementation
  - agent: Worker Specialist
    focus: Code implementation
    deliverables:
      - pyproject.toml
      - .env.example
      - Initial project structure

# REVIEW PIPELINE (Sekvenčný)
review_pipeline:
  iteration_1:
    - agent: Code Analyzer
      checks:
        - Security vulnerability scan (Bandit)
        - Type checking (mypy --strict)
        - Code quality metrics (radon)

    - agent: Code Reviewer
      review_type: "Security-focused review"
      checklist:
        - [ ] No hardcoded secrets
        - [ ] Proper exception handling
        - [ ] Rate limiting implemented
        - [ ] GDPR fields on models
        - [ ] Input sanitization complete

    - agent: Production Validator
      gates:
        - All security checks pass
        - Type coverage > 95%
        - No critical vulnerabilities

  iteration_2_if_needed:
    trigger: "Any review failure"
    agents:
      - Worker Specialist (fixes)
      - Code Reviewer (re-review)

commit_message: "feat(core): add infrastructure with security layer"
```

---

### FÁZA 2: DOMAIN MODELS
**Paralelné agenty:** 2

```yaml
stage: domain_models

agents_deployed:
  - agent: Code Goal Planner
    tasks:
      - Design domain models with GDPR compliance
      - Create Pydantic v2 models
    deliverables:
      - src/lead_gen/models/lead.py
      - src/lead_gen/models/outreach.py
      - src/lead_gen/models/workflow.py

  - agent: Database Specialist
    tasks:
      - Design persistence layer (if needed)
      - Data validation schemas
      - Migration strategy

review_pipeline:
  - agent: Code Analyzer
    focus: Model validation, field types

  - agent: Code Reviewer
    checklist:
      - [ ] All GDPR required fields present
      - [ ] Proper Pydantic validators
      - [ ] Serialization tested
      - [ ] Documentation complete

  - agent: TDD London Swarm
    tests_required:
      - Unit tests for all models
      - Validation edge cases
      - Serialization round-trip

min_coverage: 90%
commit_message: "feat(models): add GDPR-compliant domain models"
```

---

### FÁZA 3: API SERVICES (Backend Core)
**Paralelné agenty:** 4

```yaml
stage: api_services
parallel_execution: true

agents_deployed:
  # Všetci 4 bežia paralelne
  - agent: Worker Specialist #1
    service: Google Places API v1
    deliverable: src/lead_gen/services/places_service.py
    requirements:
      - Async implementation
      - Rate limiting integration
      - Error handling with circuit breaker

  - agent: Worker Specialist #2
    service: OpenAI API
    deliverable: src/lead_gen/services/openai_service.py
    requirements:
      - Slovak language prompts
      - Prompt injection prevention
      - Token counting

  - agent: Worker Specialist #3
    service: Google Sheets
    deliverable: src/lead_gen/services/sheets_service.py
    requirements:
      - Batch operations
      - Service account auth

  - agent: Worker Specialist #4
    service: Hunter.io
    deliverable: src/lead_gen/services/hunter_service.py
    requirements:
      - Email verification
      - Rate limiting
      - Graceful degradation

# INTEGRATION TESTING
integration_review:
  - agent: Integration Architect
    validation:
      - Service contracts match
      - Error propagation correct
      - Circuit breakers configured

  - agent: Performance Engineer V2
    benchmarks:
      - Response time < 500ms per service
      - Memory footprint acceptable
      - Connection pooling verified

# CODE REVIEW GATE
review_pipeline:
  - agent: Code Analyzer
    scans:
      - API key exposure check
      - Async best practices
      - Exception handling patterns

  - agent: Code Reviewer
    review_focus: "API integration patterns"
    checklist:
      - [ ] All services async
      - [ ] Proper timeout handling
      - [ ] Retry logic with backoff
      - [ ] Logging with correlation IDs
      - [ ] No blocking calls

  - agent: TDD London Swarm
    tests:
      - VCR cassettes for API responses
      - Mock service tests
      - Error scenario coverage

commit_message: "feat(services): add async API services with resilience"
```

---

### FÁZA 4: TOOLS LAYER
**Paralelné agenty:** 2

```yaml
stage: tools_layer

agents_deployed:
  - agent: Master GOAP Agent
    role: Orchestrate tool design
    planning:
      - Decompose tool requirements
      - Define preconditions/effects
      - Create execution graph

  - agent: Worker Specialist
    implementation:
      - src/lead_gen/tools/base.py
      - src/lead_gen/tools/scrape_leads.py
      - src/lead_gen/tools/generate_outreach.py
      - src/lead_gen/tools/export_to_sheets.py
      - src/lead_gen/tools/enrich_email.py

review_pipeline:
  - agent: Code Analyzer
  - agent: Code Reviewer
    checklist:
      - [ ] BaseTool abstraction clean
      - [ ] Each tool single responsibility
      - [ ] Proper error propagation
      - [ ] Logging comprehensive

  - agent: Production Validator
    gates:
      - All tools instantiable
      - Dependencies injectable
      - Integration tests pass

commit_message: "feat(tools): add modular tool layer"
```

---

### FÁZA 5: WORKFLOW ORCHESTRATION
**Paralelné agenty:** 2

```yaml
stage: workflow_orchestration

agents_deployed:
  - agent: Queen Coordinator V3
    role: Design workflow orchestration
    coordination:
      - Multi-step workflow design
      - Error recovery paths
      - State management

  - agent: Code Goal Planner
    implementation:
      - src/lead_gen/workflows/base.py
      - src/lead_gen/workflows/lead_generation.py
      - workflows/slovakia_dentists.yaml

review_pipeline:
  - agent: Integration Architect
    validation:
      - Workflow steps correctly ordered
      - Error handling complete
      - Rollback capabilities

  - agent: Code Reviewer
  - agent: TDD London Swarm
    e2e_tests:
      - Complete workflow execution
      - Partial failure recovery
      - YAML config validation

commit_message: "feat(workflows): add orchestration layer"
```

---

### FÁZA 6: CLI INTERFACE
**Sekvenčný agent:** 1

```yaml
stage: cli

agents_deployed:
  - agent: Worker Specialist
    deliverables:
      - src/lead_gen/cli.py (Click-based)
      - Entry point configuration

review_pipeline:
  - agent: Code Reviewer
  - agent: Production Validator
    validation:
      - CLI help text clear
      - Error messages user-friendly
      - Exit codes correct

commit_message: "feat(cli): add command-line interface"
```

---

### FÁZA 7: DOCKER DEPLOYMENT
**Paralelné agenty:** 2

```yaml
stage: docker_deployment

agents_deployed:
  - agent: Security Architect
    focus: Container security
    deliverables:
      - Dockerfile (multi-stage, non-root)
      - .dockerignore

  - agent: Performance Engineer V2
    focus: Optimization
    deliverables:
      - docker-compose.yml
      - Resource limits configuration
      - Health check endpoints

review_pipeline:
  - agent: Code Analyzer
    security_scan:
      - Trivy container scan
      - No root privileges
      - Read-only filesystem

  - agent: Production Validator
    gates:
      - Container builds successfully
      - Health checks pass
      - Resource limits enforced
      - Secrets not in image

commit_message: "feat(deploy): add secure Docker deployment"
```

---

### FÁZA 8: FRONTEND DASHBOARD (Paralelne s Backend)
**Paralelné agenty:** 3

```yaml
stage: frontend
parallel_with: backend_phases

agents_deployed:
  # DESIGN TEAM
  - agent: Enterprise Design System
    deliverables:
      - Design tokens
      - Component library specification
      - UI/UX wireframes

  - agent: Accessibility Agent
    requirements:
      - WCAG 2.1 AA compliance
      - Keyboard navigation
      - Screen reader support

  - agent: Design Iterator
    iterations:
      - Prototype v1
      - User feedback integration
      - Refinement v2

frontend_stack:
  framework: React/Next.js or Svelte
  styling: Tailwind CSS + shadcn/ui
  charts: Recharts for metrics

pages:
  - Dashboard (lead metrics, recent activity)
  - Lead Browser (filter, search, export)
  - Workflow Runner (start/stop workflows)
  - Settings (API keys, preferences)
  - GDPR Center (data export, deletion requests)

review_pipeline:
  - agent: Performance Agent
    metrics:
      - FCP < 1.5s
      - LCP < 2.5s
      - CLS < 0.1

  - agent: Accessibility Agent
    audit:
      - Lighthouse accessibility score > 95
      - axe-core zero violations

  - agent: Code Reviewer
    frontend_checklist:
      - [ ] Responsive design
      - [ ] Dark mode support
      - [ ] Error boundaries
      - [ ] Loading states
      - [ ] Proper TypeScript types

commit_message: "feat(frontend): add enterprise dashboard"
```

---

### FÁZA 9: TESTING & CI/CD
**Paralelné agenty:** 2

```yaml
stage: testing_cicd

agents_deployed:
  - agent: TDD London Swarm
    coverage_targets:
      unit: 80%
      integration: 70%
      e2e: 50%
    deliverables:
      - tests/unit/
      - tests/integration/
      - tests/e2e/
      - conftest.py with fixtures

  - agent: Benchmark Suite
    deliverables:
      - Performance baselines
      - Load test scripts
      - Benchmark reports

cicd_setup:
  agent: Worker Specialist
  deliverables:
    - .github/workflows/ci.yml
    - .github/workflows/deploy.yml
    - .pre-commit-config.yaml

review_pipeline:
  - agent: Production Validator
    final_gates:
      - All tests pass
      - Coverage thresholds met
      - Security scans clean
      - Docker builds succeed
      - Documentation complete

commit_message: "feat(testing): add comprehensive test suite and CI/CD"
```

---

### FÁZA 10: FINAL VALIDATION
**Sekvenčný gate**

```yaml
stage: final_validation

agents_deployed:
  - agent: Production Validator
    comprehensive_audit:
      - Security checklist (23 items from critical analysis)
      - GDPR compliance verification
      - Performance benchmarks
      - Documentation review
      - Deployment readiness

  - agent: Code Analyzer
    final_scan:
      - Full codebase analysis
      - Technical debt assessment
      - Architecture compliance

approval_required_from:
  - Production Validator: PASS
  - Security Architect: APPROVED
  - Legal Advisor: COMPLIANT

final_commit_message: "release: Lead-Gen v1.0.0 - Production Ready"
```

---

## ITERATÍVNY REVIEW PROCES

Každá fáza prechádza minimálne jedným cyklom review:

```
┌─────────────────────────────────────────────────────────────────────┐
│                     REVIEW ITERATION CYCLE                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐             │
│  │ Development │───→│ Code        │───→│ Code        │             │
│  │ Complete    │    │ Analyzer    │    │ Reviewer    │             │
│  └─────────────┘    │ (Automated) │    │ (Manual)    │             │
│                     └─────────────┘    └──────┬──────┘             │
│                                               │                     │
│                     ┌─────────────────────────┼─────────────────┐  │
│                     │                         ▼                 │  │
│                     │  ┌─────────────────────────────────────┐  │  │
│                     │  │         REVIEW DECISION             │  │  │
│                     │  ├─────────────────────────────────────┤  │  │
│                     │  │  APPROVED → Production Validator    │  │  │
│                     │  │  CHANGES_REQUESTED → Fix & Re-review│  │  │
│                     │  │  BLOCKED → Escalate to Human        │  │  │
│                     │  └─────────────────────────────────────┘  │  │
│                     │                         │                 │  │
│                     └─────────────────────────┼─────────────────┘  │
│                                               ▼                     │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐             │
│  │ Commit &    │←───│ Production  │←───│ Tests       │             │
│  │ Push        │    │ Validator   │    │ Pass        │             │
│  └─────────────┘    └─────────────┘    └─────────────┘             │
│                                                                     │
│  Minimum Iterations: 1                                              │
│  Maximum Iterations: 3 (then escalate to human)                     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Review Checklisty

#### Security Review Checklist
```markdown
- [ ] No hardcoded secrets (grep -r "api_key\|password\|secret")
- [ ] Proper input validation (all user inputs sanitized)
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (output encoding)
- [ ] CSRF protection (tokens on state-changing operations)
- [ ] Rate limiting implemented
- [ ] Authentication/Authorization proper
- [ ] Logging without sensitive data
- [ ] Dependencies vulnerability-free (safety check)
- [ ] Docker running as non-root
```

#### Code Quality Checklist
```markdown
- [ ] Type hints on all functions
- [ ] Docstrings on public APIs
- [ ] No code duplication (DRY)
- [ ] Single responsibility principle
- [ ] Proper error handling (no bare except)
- [ ] Async/await properly used
- [ ] No blocking calls in async code
- [ ] Consistent naming conventions
- [ ] Reasonable function length (<50 lines)
- [ ] Comprehensive unit tests
```

#### GDPR Compliance Checklist
```markdown
- [ ] Legal basis documented for each data processing
- [ ] Data minimization (only necessary fields collected)
- [ ] Purpose limitation (data used only for stated purpose)
- [ ] Storage limitation (retention policy implemented)
- [ ] Right to access (export endpoint exists)
- [ ] Right to erasure (deletion endpoint exists)
- [ ] Consent management (if applicable)
- [ ] Data processing records maintained
- [ ] Privacy policy accessible
- [ ] DPO contact information available
```

---

## PARALELIZÁCIA AGENTOV

### Maximálna Paralelizácia

```
Timeline (Concurrent Execution)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Week 1:
├── [Legal Advisor]──────────────────────────────────────────────────
├── [Security Architect]─────────────────────────────────────────────
└── [Queen Coordinator V3] (planning)────────────────────────────────

Week 2:
├── [Integration Architect]──[API Services x4 parallel]──────────────
├── [Worker Specialist #1-4]─────────────────────────────────────────
├── [Enterprise Design System]───────────────────────────(frontend)──
└── [Code Reviewer]────────────(reviews each completion)─────────────

Week 3:
├── [Worker Specialist]──────[Tools Layer]───────────────────────────
├── [Queen Coordinator]──────[Workflows]─────────────────────────────
├── [Accessibility Agent]────────────────────────(frontend cont.)────
└── [TDD London Swarm]───────(testing parallel)──────────────────────

Week 4:
├── [Performance Engineer]───[Docker Optimization]───────────────────
├── [Benchmark Suite]────────[Performance Testing]───────────────────
├── [Production Validator]───────────────(final gates)───────────────
└── [Design Iterator]────────────────────(frontend polish)───────────

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## HANDOFF PROTOKOL

Po dokončení každej fázy:

```yaml
handoff_protocol:
  1_commit:
    agent: Worker Specialist
    action: "git add -A && git commit -m '<message>'"

  2_push:
    agent: Worker Specialist
    action: "git push -u origin <branch>"

  3_notify:
    agent: Swarm Memory Manager
    action: "Update shared state with completion status"

  4_trigger_review:
    agent: Code Reviewer
    action: "Initiate review cycle"

  5_next_phase:
    agent: Queen Coordinator V3
    action: "Dispatch next phase agents"
    condition: "review.status == APPROVED"
```

---

## ZHRNUTIE

### Celkový počet agentov: 47+
### Vybraní kľúčoví agenti: 15
### Paralelne bežiaci v jednom čase: max 4

### Garantované Quality Gates:
1. **Code Analyzer** - Automatizovaná analýza
2. **Code Reviewer** - Manuálny review
3. **Production Validator** - Final gate
4. **TDD London Swarm** - Testovanie

### Minimálne iterácie review: 1 per fáza
### Maximálne iterácie pred eskaláciou: 3

---

*Dokument vytvorený: 2026-01-28*
*Architekt: Claude Opus 4.5 + Agent Swarm*
