---
paths:
  - "**/*.ts"
---

# Electron Security Rules

## Context Isolation
- `contextIsolation: true` - ALWAYS enabled
- `nodeIntegration: false` - in renderer processes
- All communication through preload.ts

## Forbidden
- No `remote` module usage
- No direct Node.js in renderer

## Sensitive Data
- Use `safeStorage` for API keys and secrets
- Never store secrets in plain text

## IPC Validation
- Validate all IPC message payloads
- Use typed channels
