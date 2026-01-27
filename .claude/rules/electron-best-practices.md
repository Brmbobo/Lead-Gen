---
paths:
  - "src/main/**/*.ts"
---

# Electron Best Practices

## Single Instance
- Use `app.requestSingleInstanceLock()`
- Handle `second-instance` event

## Window Lifecycle
- Close vs hide for tray apps
- Proper cleanup of listeners

## Memory Management
- Remove event listeners on cleanup
- Dispose windows properly

## App Lifecycle
- Wait for `ready` event before window creation
- Handle `activate` event for macOS
