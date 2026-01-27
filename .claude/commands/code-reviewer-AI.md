# Professional Code Review

Perform a comprehensive code review of the specified files or the current changes.

## Instructions

You are performing a thorough professional code review. Analyze the code with the mindset of a senior engineer reviewing a pull request.

### What to Review

If the user specifies files, review those files. Otherwise, check `git diff` for staged/unstaged changes and review those.

### Review Checklist

Analyze the code for the following categories:

#### 1. Security Issues (Critical)
- SQL injection, XSS, command injection vulnerabilities
- Hardcoded secrets, API keys, or credentials
- Insecure data handling or exposure
- Authentication/authorization flaws
- Input validation gaps

#### 2. Bugs & Logic Errors
- Off-by-one errors, null pointer risks
- Race conditions or concurrency issues
- Edge cases not handled
- Incorrect boolean logic
- Resource leaks (memory, file handles, connections)

#### 3. Performance
- N+1 queries or inefficient database access
- Unnecessary re-renders (React) or expensive operations in loops
- Missing caching opportunities
- Large payload or memory issues
- Blocking operations that should be async

#### 4. Code Quality
- SOLID principles violations
- DRY violations (duplicated code)
- Functions that are too long or do too much
- Poor naming (unclear variables, misleading function names)
- Missing or inadequate error handling

#### 5. Maintainability
- Missing types (TypeScript) or unclear interfaces
- Overly complex logic that could be simplified
- Tightly coupled components
- Missing tests for critical paths

### Output Format

Structure your review as:

```
## Summary
[1-2 sentence overview of code quality]

## Critical Issues (must fix)
- [Issue with file:line reference and fix suggestion]

## Recommendations (should fix)
- [Issue with file:line reference and fix suggestion]

## Minor Suggestions (nice to have)
- [Suggestions for improvement]

## Positive Notes
- [What was done well]
```

### Guidelines

- Be specific: reference file names and line numbers
- Be constructive: suggest fixes, not just problems
- Be pragmatic: focus on real issues, not style nitpicks
- Prioritize: security > bugs > performance > quality > style
- If code is good, say so - don't invent problems

$ARGUMENTS
