# n8n Workflow Architect

Strategic automation architecture advisor based on the Intelligent Automation Architect (IAA) Protocol.

## Purpose

This skill helps users make informed decisions about automation architecture **before** building. It answers the fundamental questions:

- Should I use n8n, Python, or a hybrid approach?
- Given my business stack, what's the path of least resistance?
- How do I make this production-ready?

## When Claude Should Use This Skill

Invoke this skill when users:

1. **Plan an automation project** - "I need to automate..."
2. **Describe their tech stack** - "I use Shopify, Zoho, HubSpot..."
3. **Ask architecture questions** - "Should I use n8n or Python?"
4. **Evaluate feasibility** - "Can I automate X?"
5. **Need production guidance** - "How do I make this reliable?"

## Contents

| File | Purpose |
|------|---------|
| [SKILL.md](SKILL.md) | Main entry point - decision framework, quick references |
| [tool-selection-matrix.md](tool-selection-matrix.md) | Detailed n8n vs Python decision criteria |
| [business-stack-analysis.md](business-stack-analysis.md) | Common SaaS platforms and integration patterns |
| [production-readiness.md](production-readiness.md) | Pre-launch checklist and operational concerns |

## Integration with Other Skills

This skill serves as the **planning layer** that coordinates with:

```
                 n8n-workflow-architect
                 (Strategic Planning)
                         │
    ┌────────────────────┼────────────────────┐
    ▼                    ▼                    ▼
n8n-workflow-      n8n-node-           n8n-validation-
patterns           configuration        expert
(Architecture)     (Node Setup)         (Quality)
    │                    │                    │
    ▼                    ▼                    ▼
n8n-code-          n8n-code-           n8n-expression-
javascript         python              syntax
(JS Logic)         (Python Logic)      (Expressions)
    │                    │                    │
    └────────────────────┼────────────────────┘
                         ▼
                   n8n MCP Tools
              (Create, Validate, Deploy)
```

### Skill Handoff Flow

1. **User describes need** → `n8n-workflow-architect` analyzes
2. **Architecture decided** → Hand off to `n8n-workflow-patterns`
3. **Nodes identified** → Hand off to `n8n-node-configuration`
4. **Code needed** → Hand off to `n8n-code-javascript` or `n8n-code-python`
5. **Expressions needed** → Hand off to `n8n-expression-syntax`
6. **Ready to validate** → Hand off to `n8n-validation-expert`
7. **Build workflow** → Use n8n MCP tools

## Key Concepts

### The Core Philosophy

> **Viability over Possibility**

The gap between what's technically possible and what's actually viable in production is enormous. Build systems that:

- Won't break at 3 AM on a Saturday
- Don't require a PhD to maintain
- Deliver actual business value

### Quick Decision Rules

| Use n8n When | Use Python When |
|--------------|-----------------|
| OAuth authentication needed | Processing > 5,000 records |
| Non-technical maintainers | Files > 20MB |
| Multi-day wait processes | Complex algorithms |
| Standard SaaS integrations | Cutting-edge AI/ML |

### Hybrid Architecture

For complex systems, combine both:

```
n8n Layer (Orchestration)
├── Webhooks, triggers, OAuth
├── User-facing integrations
└── Flow coordination

Python Layer (Processing)
├── Heavy computation
├── Complex logic
└── AI/ML operations
```

## Usage Examples

### Example 1: E-commerce Stack Analysis

**User**: "I use Shopify, Klaviyo, and Slack. How should I automate order notifications?"

**Architect Response**:
- All services have native n8n nodes
- OAuth managed automatically
- Standard webhook patterns apply
- **Recommendation**: Pure n8n
- **Hand off to**: `n8n-workflow-patterns` → webhook_processing

### Example 2: AI-Powered Lead Scoring

**User**: "I need AI to score leads from Typeform and update HubSpot"

**Architect Response**:
- Typeform/HubSpot via n8n (OAuth)
- AI scoring logic is complex
- **Recommendation**: Hybrid
- n8n for integrations, Code node for AI logic
- **Hand off to**: `n8n-workflow-patterns` → ai_agent_workflow

### Example 3: Large Data Pipeline

**User**: "Daily sync of 50,000 records from Postgres to BigQuery"

**Architect Response**:
- Volume exceeds n8n memory limits
- **Recommendation**: Python with n8n trigger
- n8n for scheduling and notifications
- Python for batch processing
- **Warning**: Rate limits, resumability needed

## Credits

Based on the Intelligent Automation Architect (IAA) Protocol - a comprehensive guide to building automation systems that survive production.
