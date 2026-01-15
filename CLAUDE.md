# Claude Code Configuration

> Uses on-demand skills for detailed guidance. See skills table below.

## Core Rules

1. **TDD Mandatory**: Write failing tests first, then implement
2. **Ask Before Acting**: Clarify ambiguous requirements
3. **Simple Solutions**: Avoid over-engineering
4. **Match Style**: Follow existing code patterns
5. **Fix Bugs Immediately**: When found during work

## Cross-Review Policy

All Claude/Gemini work must be reviewed by Codex (max 3 iterations).
See `cross-review-policy` skill for details.

## On-Demand Skills

Load these when the task requires detailed guidance:

| Need | Skill | When |
|------|-------|------|
| AI workflow rules | `ai-agent-guidelines` | Code review, agent tasks |
| Cross-review process | `cross-review-policy` | Before presenting work |
| Development workflow | `dev-workflow` | YAML/pseudocode/TDD |
| File organization | `file-org-standards` | Creating files/dirs |
| Testing standards | `testing-standards` | Writing tests |
| Logging standards | `logging-standards` | Adding logging |

**Skill path:** `@~/.claude/skills/<category>/<skill-name>/SKILL.md`

## Quick Commands

```bash
# From workspace-hub
./scripts/workspace              # Main CLI
./scripts/repository_sync        # Git operations
```

---
*Skills provide detailed guidance without consuming context. Reference when needed.*

