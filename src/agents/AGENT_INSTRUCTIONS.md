# BlackRoad Agent Instructions & Todo System

## Overview

This document provides instructions for AI agents (Claude, automation bots, CI/CD workflows) working on the BlackRoad AI Inference Accelerator project. Following these guidelines ensures successful pull requests and proper integration across all endpoints.

---

## Agent Types & Responsibilities

### 1. Claude Code Agent
**Primary Role**: Code implementation, PR creation, endpoint integration

**Capabilities**:
- Read/Write/Edit files
- Execute bash commands
- Search codebase (Glob, Grep)
- Web fetch for documentation
- Git operations

**Branch Naming**: `claude/{task-description}-{session-id}`

### 2. Explore Agent
**Primary Role**: Codebase analysis, architecture understanding

**Capabilities**:
- Comprehensive file search
- Code pattern analysis
- Dependency mapping

### 3. Plan Agent
**Primary Role**: Implementation strategy, task breakdown

**Capabilities**:
- Architecture design
- Task decomposition
- Risk assessment

### 4. Bash Agent
**Primary Role**: System operations, deployments

**Capabilities**:
- Command execution
- Git operations
- Build processes

---

## Pre-PR Checklist (CRITICAL)

Before creating any pull request, agents MUST complete these steps:

### Step 1: Verify Branch
```bash
git branch --show-current
# Must match: claude/{task}-{session-id}
```

### Step 2: Run Hash Verification
```python
from src.hashing.sha_infinity import KanbanHasher

hasher = KanbanHasher()
report = hasher.get_integrity_report()
assert report['valid'], f"Integrity check failed: {report['errors']}"
```

### Step 3: Validate Endpoints
```bash
python scripts/validate_endpoints.py --all
# All configured endpoints must be reachable
```

### Step 4: Sync State
```bash
python scripts/sync_state.py --source github --targets salesforce,cloudflare
# State must be synchronized before PR
```

### Step 5: Compute PR Hash
```python
from src.hashing.sha_infinity import KanbanHasher

hasher = KanbanHasher()
pr_hash = hasher.hash_pr(
    pr_number=PR_NUMBER,
    title=PR_TITLE,
    branch=BRANCH_NAME,
    status="ready_for_review",
    files_changed=CHANGED_FILES,
    commits=COMMIT_SHAS
)
# Include this hash in PR description
```

---

## Todo Management Protocol

### Creating Todos

When starting a task, immediately create a todo list:

```python
# Example todo structure for kanban system
todos = [
    {
        "content": "Research existing endpoint configurations",
        "status": "in_progress",
        "activeForm": "Researching endpoint configurations"
    },
    {
        "content": "Design API schema for new endpoint",
        "status": "pending",
        "activeForm": "Designing API schema"
    },
    {
        "content": "Implement endpoint handler",
        "status": "pending",
        "activeForm": "Implementing endpoint handler"
    },
    {
        "content": "Add tests for endpoint",
        "status": "pending",
        "activeForm": "Adding endpoint tests"
    },
    {
        "content": "Update documentation",
        "status": "pending",
        "activeForm": "Updating documentation"
    }
]
```

### Todo State Transitions

```
pending -> in_progress -> completed
                |
                v
           (blocked) -> Create new todo for blocker
```

### Rules
1. Only ONE todo should be `in_progress` at a time
2. Mark todos `completed` IMMEDIATELY after finishing
3. Never mark incomplete work as done
4. Create sub-todos for complex tasks
5. Include hash verification in final todo

---

## Kanban Card Integration

### Creating Cards via Agent

```python
from src.kanban.board import KanbanBoard

board = KanbanBoard()

# Create a new card
card = board.create_card(
    type="agent_task",
    title="Implement Cloudflare KV sync",
    description="Set up state synchronization with Cloudflare KV",
    assignee="claude-agent",
    priority="P1",
    labels=["integration", "cloudflare"],
    agent_metadata={
        "session_id": SESSION_ID,
        "branch": BRANCH_NAME,
        "max_attempts": 3
    }
)

# Move card through pipeline
board.move_card(card.id, "in_progress")
# ... do work ...
board.move_card(card.id, "review")
```

### Card Status Mapping

| Kanban Status | PR Status | Agent Action |
|--------------|-----------|--------------|
| backlog | - | Plan task |
| qualified | draft | Start implementation |
| in_progress | open | Active development |
| review | ready_for_review | Request review |
| staging | approved | Pre-merge testing |
| deployed | merged | Post-merge verification |

---

## Endpoint Integration Guidelines

### Required Validations Per Endpoint

#### Cloudflare
```python
# Verify KV namespace access
cloudflare.kv.get("BLACKROAD_STATE", "health_check")

# Verify Workers deployment capability
cloudflare.workers.validate_script(script_content)
```

#### Salesforce
```python
# Verify OAuth token
salesforce.auth.refresh_token()

# Verify custom object access
salesforce.sobjects.describe("BlackRoad_Project__c")
```

#### Vercel
```python
# Verify project access
vercel.projects.get(project_id)

# Verify deployment permissions
vercel.deployments.create_preview(branch)
```

#### Claude API
```python
# Verify API key
claude.messages.create(
    model="claude-haiku-3-5-20241022",
    messages=[{"role": "user", "content": "ping"}],
    max_tokens=10
)
```

#### Raspberry Pi Fleet
```python
# Health check all nodes
for node in pi_fleet.nodes:
    response = node.health_check()
    assert response.status == "healthy"
```

---

## PR Failure Prevention

### Common Failure Causes & Solutions

#### 1. State Desync
**Symptom**: PR conflicts with CRM state
**Solution**: Always sync before PR creation
```bash
python scripts/sync_state.py --force --all
```

#### 2. Missing Hash Verification
**Symptom**: Integrity check fails in CI
**Solution**: Include PR hash in description
```markdown
## Integrity
- PR Hash: `INF:42:0000abc123...`
- Chain Valid: true
- Merkle Root: `def456...`
```

#### 3. Endpoint Unreachable
**Symptom**: Integration tests fail
**Solution**: Validate endpoints before PR
```bash
python scripts/validate_endpoints.py --retry 3 --backoff
```

#### 4. Branch Naming
**Symptom**: Push rejected
**Solution**: Use correct format
```bash
# Correct
git checkout -b claude/add-salesforce-sync-abc123

# Wrong
git checkout -b feature/salesforce
```

#### 5. Missing Todos
**Symptom**: Incomplete implementation merged
**Solution**: Always track with TodoWrite
```python
# At start of task
TodoWrite(todos=[...])

# After each step
TodoWrite(todos=[...update status...])
```

---

## State Synchronization Protocol

### Sync Flow

```
GitHub (Source of Truth for Code)
    |
    v
Salesforce CRM (Primary State Store)
    |
    +---> Cloudflare KV (Edge Cache)
    |
    +---> GitHub Projects (Kanban View)
    |
    +---> Local Agent State (Working Memory)
```

### Sync Commands

```bash
# Full sync
python scripts/sync_state.py --all

# Specific platform
python scripts/sync_state.py --target salesforce

# Conflict resolution
python scripts/sync_state.py --resolve last_write_wins
```

### State Schema

```json
{
  "card_id": "CARD-001",
  "title": "Task title",
  "status": "in_progress",
  "assignee": "claude-agent",
  "priority": "P1",
  "sha_hash": "abc123...",
  "last_sync": {
    "github": "2026-01-27T10:00:00Z",
    "salesforce": "2026-01-27T10:00:01Z",
    "cloudflare": "2026-01-27T10:00:02Z"
  },
  "integrity": {
    "merkle_root": "def456...",
    "infinity_hash": "INF:42:0000..."
  }
}
```

---

## Agent Task Templates

### Template: New Endpoint Integration

```markdown
## Task: Integrate {ENDPOINT_NAME}

### Todos
1. [ ] Research {ENDPOINT_NAME} API documentation
2. [ ] Add configuration to config/endpoints.yaml
3. [ ] Implement client in src/endpoints/{endpoint}.py
4. [ ] Add health check handler
5. [ ] Create sync adapter for state management
6. [ ] Add tests
7. [ ] Update AGENT_INSTRUCTIONS.md
8. [ ] Compute and verify hashes
9. [ ] Create PR with integrity report

### Acceptance Criteria
- [ ] Endpoint reachable from all nodes
- [ ] State syncs within 30s
- [ ] Hash chain remains valid
- [ ] No regression in existing integrations
```

### Template: Bug Fix

```markdown
## Task: Fix {BUG_DESCRIPTION}

### Todos
1. [ ] Reproduce the bug
2. [ ] Identify root cause
3. [ ] Implement fix
4. [ ] Add regression test
5. [ ] Verify hash integrity
6. [ ] Create PR

### Integrity
- Card Hash: {COMPUTE_HASH}
- Affected Endpoints: {LIST}
```

### Template: Feature Implementation

```markdown
## Task: Implement {FEATURE_NAME}

### Todos
1. [ ] Design feature architecture
2. [ ] Break down into sub-tasks
3. [ ] Implement core functionality
4. [ ] Add endpoint integrations
5. [ ] Implement state sync
6. [ ] Add comprehensive tests
7. [ ] Document in README
8. [ ] Verify all hashes
9. [ ] Create PR with full integrity report

### State Sync Requirements
- Primary: Salesforce
- Mirrors: Cloudflare KV, GitHub Projects
- Sync Interval: 30s
```

---

## Quick Reference Commands

```bash
# Start new task
git checkout -b claude/{task}-{session_id}
python scripts/init_task.py --title "{TASK_TITLE}"

# Validate before commit
python scripts/pre_commit.py

# Full integrity check
python -c "from src.hashing.sha_infinity import KanbanHasher; print(KanbanHasher().get_integrity_report())"

# Sync state
python scripts/sync_state.py --all

# Validate endpoints
python scripts/validate_endpoints.py --all

# Create PR
gh pr create --title "{TITLE}" --body "$(cat .blackroad/pr_template.md)"

# Push with retry
git push -u origin $(git branch --show-current) || sleep 2 && git push -u origin $(git branch --show-current)
```

---

## Contact & Escalation

- **Repository**: BlackRoad-OS/blackroad-ai-inference-accelerator
- **Primary Branch**: main
- **Agent Branches**: claude/*
- **State Store**: Salesforce CRM
- **Edge Cache**: Cloudflare KV
- **Monitoring**: Prometheus + Grafana

For failed PRs, check:
1. CI logs
2. Integrity report
3. State sync status
4. Endpoint health

---

*Last Updated: 2026-01-27*
*Version: 1.0.0*
*Maintained by: BlackRoad OS Team*
