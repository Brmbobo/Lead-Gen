# Lead-Gen Implementation Plan v2.0
## Multi-Agent Orchestration with Iterative Review

> **Vytvorené:** 2026-01-29
> **Metodológia:** Google Senior Developer Best Practices
> **Workflow:** 2 Implementers → Critics → 2x Iterácia → Tests → Iterácia

---

## KOMPLETNÝ ZOZNAM DOSTUPNÝCH AGENTOV (47)

### TIER S: STRATEGIC ORCHESTRATORS
| # | Agent | Súbor | Špecializácia |
|---|-------|-------|---------------|
| 1 | **Queen Coordinator V3** | `hive-mind/queen-coordinator.md` | Swarm orchestration, 15-agent coordination |
| 2 | **Master GOAP Agent** | `goal/agent.md` (51KB) | A* planning, state modeling |
| 3 | **Goal Planner** | `goal/goal-planner.md` | Dynamic goal decomposition |
| 4 | **Code Goal Planner** | `goal/code-goal-planner.md` | Code-specific planning |
| 5 | **Collective Intelligence** | `hive-mind/collective-intelligence-coordinator.md` | Multi-agent fusion |

### TIER A: ARCHITECTS & EXPERTS
| # | Agent | Súbor | Špecializácia |
|---|-------|-------|---------------|
| 6 | **Security Architect** | `architecture-system-design/security-architect.md` | GDPR, Vault, threats |
| 7 | **Integration Architect** | `architecture-system-design/integration-architect.md` | API design, contracts |
| 8 | **Arch System Design** | `architecture-system-design/arch-system-design.md` | Architecture decisions |
| 9 | **Database Specialist** | `analysis/database-specialist.yaml` | Data persistence |

### TIER B: CODE QUALITY & REVIEW
| # | Agent | Súbor | Špecializácia |
|---|-------|-------|---------------|
| 10 | **Code Reviewer** | `code-reviewer/code-reviewer.md` | Manual code review |
| 11 | **Code Analyzer** | `analysis/code-analyzer.md` | Automated analysis |
| 12 | **Analyze Code Quality** | `analysis/analyze-code-quality.md` | Quality metrics |

### TIER C: WORKERS & IMPLEMENTERS
| # | Agent | Súbor | Špecializácia |
|---|-------|-------|---------------|
| 13 | **Worker Specialist** | `hive-mind/worker-specialist.md` | Task execution |
| 14 | **Scout Explorer** | `hive-mind/scout-explorer.md` | Reconnaissance |
| 15 | **Swarm Memory Manager** | `hive-mind/swarm-memory-manager.md` | Shared state |
| 16 | **Project Coordinator** | `project coordinator/project-coordinator.yaml` | PM coordination |

### TIER D: TESTING & VALIDATION
| # | Agent | Súbor | Špecializácia |
|---|-------|-------|---------------|
| 17 | **Production Validator** | `testing/production-validator.md` | Release gates |
| 18 | **TDD London Swarm** | `testing/tdd-london-swarm.md` | Test-driven development |
| 19 | **Test Architect** | `testing/test-architect.yaml` | Test strategy |

### TIER E: OPTIMIZATION
| # | Agent | Súbor | Špecializácia |
|---|-------|-------|---------------|
| 20 | **Performance Engineer V2** | `optimization/performance-engineer_v2.md` | Performance tuning |
| 21 | **Memory Specialist V2** | `optimization/memory-specialist_v2.md` | Memory management |
| 22 | **Performance Monitor** | `optimization/performance-monitor.md` | Monitoring |
| 23 | **Resource Allocator** | `optimization/resource-allocator.md` | Resource distribution |
| 24 | **Topology Optimizer** | `optimization/topology-optimizer.md` | System topology |
| 25 | **Load Balancer** | `optimization/load-balancer.md` | Load distribution |
| 26 | **Benchmark Suite** | `optimization/benchmark-suite.md` | Benchmarking |

### TIER F: FRONTEND & DESIGN
| # | Agent | Súbor | Špecializácia |
|---|-------|-------|---------------|
| 27 | **Enterprise Design System** | `enterprise-frontend-design/SKILL.md` | Design system |
| 28 | **Accessibility Agent** | `enterprise-frontend-design/agents/accessibility.md` | WCAG compliance |
| 29 | **Animation Agent** | `enterprise-frontend-design/agents/animation.md` | Motion design |
| 30 | **Design Iterator** | `enterprise-frontend-design/agents/design-iterator.md` | Design refinement |
| 31 | **Design System Agent** | `enterprise-frontend-design/agents/design-system.md` | Components |
| 32 | **Enterprise Patterns** | `enterprise-frontend-design/agents/enterprise-patterns.md` | B2B patterns |
| 33 | **Performance (FE)** | `enterprise-frontend-design/agents/performance.md` | FCP/LCP |

### TIER G: DEBUGGING & MAINTENANCE
| # | Agent | Súbor | Špecializácia |
|---|-------|-------|---------------|
| 34 | **Debugger** | `debugger/debugger.md` | Debugging specialist |

---

## ZISTENIA Z ANALÝZY (5 AGENTOV)

### Scout Explorer - Codebase Mapping
```
✅ Completeness Score: 78/100
✅ 28 Python modules, 7,747+ LOC
❌ Integration tests: 0
❌ E2E tests: 0
❌ Frontend pages: Only dashboard stub
```

### Code Analyzer - Security Audit
```
✅ No hardcoded secrets
✅ GDPR compliance framework
✅ Input sanitization (prompt injection, XSS)
⚠️ HIGH: Missing .gitignore
⚠️ MEDIUM: GDPR in-memory storage
⚠️ MEDIUM: No automatic data deletion
```

### Integration Architect - API Review
```
✅ Overall Score: A- (92/100)
✅ All services production-ready
✅ Rate limiting implemented
✅ Circuit breaker pattern
✅ Retry with exponential backoff
```

### Performance Engineer - Bottlenecks
```
❌ CRITICAL: Sequential batch processing (80% throughput loss)
❌ CRITICAL: No concurrent operations
⚠️ Unbounded memory in ToolContext
⚠️ No caching layer
Potential improvement: 5-10x throughput
```

### Test Architect - Coverage Gaps
```
❌ Current coverage: 22-28%
❌ Target: 80%
❌ Gap: 320+ tests needed
❌ 16 untested modules
```

---

## IMPLEMENTAČNÝ PLÁN

### WORKFLOW PROCES
```
┌─────────────────────────────────────────────────────────────────────┐
│                    IMPLEMENTATION WORKFLOW                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  STEP 1: IMPLEMENT (2 Agents Parallel)                              │
│  ╔═══════════════╗    ╔═══════════════╗                            │
│  ║ Agent A       ║    ║ Agent B       ║                            │
│  ║ (Specialist)  ║    ║ (Specialist)  ║                            │
│  ╚═══════╤═══════╝    ╚═══════╤═══════╝                            │
│          └────────────────────┘                                     │
│                    │                                                │
│                    ▼                                                │
│  STEP 2: CRITIC REVIEW (2 Agents Sequential)                        │
│  ╔═══════════════╗    ╔═══════════════╗                            │
│  ║ Code Analyzer ║ →  ║ Code Reviewer ║                            │
│  ║ (Automated)   ║    ║ (Manual)      ║                            │
│  ╚═══════════════╝    ╚═══════════════╝                            │
│                    │                                                │
│          ┌────────┴────────┐                                        │
│          ▼                 ▼                                        │
│     [APPROVED]        [CHANGES]                                     │
│          │                 │                                        │
│          │    ┌────────────┘                                        │
│          │    ▼                                                     │
│          │  ITERATION 1: Fix issues                                 │
│          │    │                                                     │
│          │    ▼                                                     │
│          │  CRITIC REVIEW again                                     │
│          │    │                                                     │
│          │    ▼                                                     │
│          │  ITERATION 2: Final fixes                                │
│          │    │                                                     │
│          └────┴────────────┐                                        │
│                            ▼                                        │
│  STEP 3: TEST (2 Agents Parallel)                                   │
│  ╔═══════════════╗    ╔═══════════════╗                            │
│  ║ TDD London    ║    ║ Production    ║                            │
│  ║ Swarm         ║    ║ Validator     ║                            │
│  ╚═══════════════╝    ╚═══════════════╝                            │
│                    │                                                │
│          ┌────────┴────────┐                                        │
│          ▼                 ▼                                        │
│     [PASS]            [FAIL]                                        │
│          │                 │                                        │
│          │    ┌────────────┘                                        │
│          │    ▼                                                     │
│          │  ITERATION: Fix test failures                            │
│          │    │                                                     │
│          └────┴────────────┐                                        │
│                            ▼                                        │
│  STEP 4: COMMIT & NEXT PAIR                                         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## FÁZA 1: CRITICAL FIXES (Okamžite)

### Pair 1.1: Security + Performance
```yaml
implementers:
  - agent: Security Architect
    tasks:
      - Create .gitignore file
      - Fix GDPR in-memory storage → SQLite/file
      - Implement automatic data deletion

  - agent: Performance Engineer V2
    tasks:
      - Implement concurrent batch processing
      - Add asyncio.gather() to batch methods
      - Add Semaphore for rate limit compliance

critics:
  - Code Analyzer (automated scan)
  - Code Reviewer (manual review)

iterations: 2

testers:
  - TDD London Swarm (unit tests)
  - Production Validator (integration)

iteration_after_tests: 1

deliverables:
  - .gitignore
  - src/lead_gen/core/gdpr.py (updated)
  - src/lead_gen/services/openai_service.py (concurrent)
  - src/lead_gen/services/hunter_service.py (concurrent)
  - tests/unit/test_concurrent_batch.py
```

---

## FÁZA 2: TEST COVERAGE (Priority)

### Pair 2.1: Circuit Breaker + Secrets
```yaml
implementers:
  - agent: Worker Specialist #1
    focus: Circuit Breaker tests
    deliverables:
      - tests/unit/test_retry_circuit_breaker.py (30 tests)

  - agent: Worker Specialist #2
    focus: Secret Management tests
    deliverables:
      - tests/unit/test_secrets_management.py (35 tests)

critics:
  - Code Analyzer
  - Code Reviewer

iterations: 2

testers:
  - TDD London Swarm
  - Benchmark Suite

coverage_target: 85%
```

### Pair 2.2: GDPR + Services
```yaml
implementers:
  - agent: Security Architect
    focus: GDPR compliance tests
    deliverables:
      - tests/unit/test_gdpr_compliance.py (40 tests)

  - agent: Integration Architect
    focus: Service tests
    deliverables:
      - tests/unit/test_openai_service.py (40 tests)
      - tests/unit/test_hunter_service.py (25 tests)

critics:
  - Code Analyzer
  - Production Validator

iterations: 2

testers:
  - TDD London Swarm
  - Test Architect

coverage_target: 80%
```

---

## FÁZA 3: INTEGRATION TESTS

### Pair 3.1: Service Integration
```yaml
implementers:
  - agent: Worker Specialist #3
    focus: Service integration
    deliverables:
      - tests/integration/test_service_integration.py (20 tests)

  - agent: Worker Specialist #4
    focus: Tool integration
    deliverables:
      - tests/integration/test_tool_integration.py (20 tests)

critics:
  - Integration Architect
  - Code Reviewer

iterations: 2

testers:
  - Production Validator
  - Benchmark Suite
```

### Pair 3.2: Workflow + E2E
```yaml
implementers:
  - agent: Code Goal Planner
    focus: Workflow tests
    deliverables:
      - tests/unit/test_workflow_base.py
      - tests/unit/test_lead_gen_workflow.py

  - agent: Worker Specialist
    focus: E2E tests
    deliverables:
      - tests/e2e/test_workflow_execution.py
      - tests/e2e/test_cli_commands.py

critics:
  - Code Analyzer
  - Production Validator

iterations: 2

testers:
  - TDD London Swarm
  - Benchmark Suite
```

---

## FÁZA 4: FRONTEND COMPLETION

### Pair 4.1: Pages + API
```yaml
implementers:
  - agent: Enterprise Design System
    focus: UI pages
    deliverables:
      - frontend/app/leads/page.tsx
      - frontend/app/messages/page.tsx
      - frontend/app/workflows/page.tsx
      - frontend/app/settings/page.tsx
      - frontend/app/gdpr/page.tsx

  - agent: Worker Specialist
    focus: API client
    deliverables:
      - frontend/lib/api.ts
      - frontend/lib/hooks.ts

critics:
  - Accessibility Agent
  - Performance (FE) Agent

iterations: 2

testers:
  - Production Validator
  - Design Iterator
```

---

## FÁZA 5: CACHING & OPTIMIZATION

### Pair 5.1: Caching Layer
```yaml
implementers:
  - agent: Performance Engineer V2
    focus: Response caching
    deliverables:
      - src/lead_gen/core/cache.py
      - Update services with caching

  - agent: Memory Specialist V2
    focus: Memory optimization
    deliverables:
      - Bounded ToolContext
      - Streaming generators

critics:
  - Code Analyzer
  - Performance Monitor

iterations: 2

testers:
  - Benchmark Suite
  - Load Balancer
```

---

## AGENT SELECTION MATRIX

### Pre Implementáciu (2 paralelne)
| Task Type | Agent A | Agent B |
|-----------|---------|---------|
| Security fixes | Security Architect | Worker Specialist |
| Performance | Performance Engineer | Memory Specialist |
| Backend code | Worker Specialist | Code Goal Planner |
| Frontend | Enterprise Design System | Worker Specialist |
| Tests | TDD London Swarm | Worker Specialist |

### Pre Review (2 sekvenčne)
| Review Type | Agent 1 | Agent 2 |
|-------------|---------|---------|
| Code quality | Code Analyzer | Code Reviewer |
| Security | Security Architect | Code Analyzer |
| Architecture | Integration Architect | Arch System Design |
| Performance | Performance Monitor | Benchmark Suite |

### Pre Testovanie (2 paralelne)
| Test Type | Agent A | Agent B |
|-----------|---------|---------|
| Unit tests | TDD London Swarm | Worker Specialist |
| Integration | Production Validator | Integration Architect |
| E2E | Production Validator | Test Architect |
| Performance | Benchmark Suite | Performance Monitor |

---

## ITERAČNÝ CYKLUS

```
Každý pár prechádza:

IMPLEMENT ────────────────────────────────────────────────
    │
    ▼
CRITIC REVIEW #1 ─────────────────────────────────────────
    │
    ├── PASS → Continue
    └── FAIL → FIX #1
                  │
                  ▼
         CRITIC REVIEW #2 ────────────────────────────────
                  │
                  ├── PASS → Continue
                  └── FAIL → FIX #2 (Final)
                               │
                               ▼
                      CRITIC REVIEW #3 ───────────────────
                               │
                               └── PASS/FAIL → Continue
                                               │
TEST ─────────────────────────────────────────────────────
    │
    ├── PASS → COMMIT
    └── FAIL → FIX
                  │
                  ▼
         TEST AGAIN ──────────────────────────────────────
                  │
                  └── PASS/FAIL → COMMIT

COMMIT & PUSH ────────────────────────────────────────────
    │
    ▼
NEXT PAIR
```

---

## ONLINE SEARCH REQUIREMENTS

Pre každú fázu hľadať aktuálne info:

```yaml
phase_1:
  search:
    - "Python asyncio.gather best practices 2026"
    - "GDPR SQLite audit log implementation"
    - "gitignore Python security best practices"

phase_2:
  search:
    - "pytest circuit breaker testing patterns"
    - "Python async mock best practices"
    - "HashiCorp Vault testing strategies"

phase_3:
  search:
    - "Python integration testing httpx"
    - "Google Places API mocking strategies"
    - "OpenAI API testing best practices"

phase_4:
  search:
    - "Next.js 14 app router best practices 2026"
    - "shadcn/ui components documentation"
    - "Tailwind CSS accessibility patterns"

phase_5:
  search:
    - "Python LRU cache async patterns"
    - "Redis caching Python best practices"
    - "Memory profiling asyncio applications"
```

---

## MCP CONTEXT7 USAGE

Pre každú knižnicu použiť context7:

```yaml
libraries_to_lookup:
  - httpx
  - pydantic v2
  - structlog
  - pytest-asyncio
  - gspread
  - openai (Python SDK)
  - hvac (Vault)
  - boto3 (AWS)
  - click
  - rich
  - Next.js 14
  - shadcn/ui
  - Tailwind CSS
```

---

## ESTIMATED TIMELINE

| Fáza | Pár | Trvanie | Iterácie |
|------|-----|---------|----------|
| 1 | Security + Performance | 2-3h | 2 + 1 |
| 2.1 | Circuit Breaker + Secrets | 3-4h | 2 + 1 |
| 2.2 | GDPR + Services | 3-4h | 2 + 1 |
| 3.1 | Service Integration | 2-3h | 2 + 1 |
| 3.2 | Workflow + E2E | 2-3h | 2 + 1 |
| 4 | Frontend | 4-5h | 2 + 1 |
| 5 | Caching | 2-3h | 2 + 1 |
| **Total** | | **18-25h** | **21 iterácií** |

---

## COMMIT STRATEGY

Po každom páre:
```bash
git add -A
git commit -m "feat(<scope>): <description>

- Agent A: <work done>
- Agent B: <work done>
- Review: <iterations>
- Tests: <coverage>

https://claude.ai/code/session_..."
git push -u origin <branch>
```

---

*Plán vytvorený: 2026-01-29*
*Metodológia: Google Senior Developer Best Practices*
*Agentov k dispozícii: 47*
*Vybraných pre implementáciu: 15-20*
