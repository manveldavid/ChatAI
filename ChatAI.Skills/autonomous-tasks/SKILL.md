---
name: autonomous-tasks
description: >
  Execute autonomous tasks and manage task lifecycle with user authentication.
  Use this skill whenever the agent receives a task file from active/
  (as the first message in a dialog) and needs to execute it, create follow-ups, or mark
  as completed. Also use when the user wants to: create a new task (provide name and pin), 
  check status of their tasks, review completed task reports, approve
  or reject task completion, or restore a task for rework. The agent operates in a cycle:
  receive task -> execute -> decide if continuation needed -> optionally create next task
  file in active/, or move to completed/ with a report. Always use when receiving a task
  file or when planning to create/complete tasks for the autonomous loop. Always use when
  the user says "create a task", "plan a task", "schedule this", "show my tasks",
  "what tasks do I have".
---

# Autonomous Tasks

This skill enables autonomous task execution with user auth, task lifecycle management,
and user-facing task review/approval.

## Architecture Loop

```
External system -> reads active/*.md
  -> sends file content as first message -> Agent receives it
  -> Agent executes task
  -> Agent decides: complete or continue?
  -> If continue: creates new task file in active/ + creates its .lock file
                  -> removes parent's .lock file
  -> If complete: creates report and moves to completed/ + removes .lock file
```

## Directory Structure

```
tasks/
├── active/                    ← Active tasks being worked on (ONLY .md files)
│   └── task-{timestamp}-{uuid}.md
└── completed/                 ← Completed reports AND per-task lock files
    ├── task-{timestamp}-{uuid}.md        ← Completed task reports
    └── task-{timestamp}-{uuid}.md.lock   ← Lock file for each ACTIVE task
```

## Lock File Architecture

Each active task has its own per-task lock file in `completed/`:
- Lock file name: `<task-filename>.lock` (e.g. `task-1234567890-abc123.md.lock`)
- Location: `completed/`
- Purpose: Signals to the external scheduler that this task needs processing
- Format: JSON with task_name, filename, current_task, previous_context, owner_hash, timestamp

Benefits:
- No race conditions — each task owns its own lock file
- Atomic operations — `os.remove()` and file creation are atomic at OS level
- Easy status check — presence of `.lock` = task awaiting processing
- Parallel-safe — multiple tasks can be created/completed independently

## Authentication

This skill delegates user authentication to the **authorize-user** skill.

Before performing any task management action (create, list, review, approve),
you MUST authenticate the user via:

```bash
python ../authorize-user/scripts/verify.py <username> <pin>
```

The script returns JSON:
- `{"success": true, "owner": "<name>", "owner_hash": "..."}` — auth passed
- `{"success": false, "error": "..."}` — auth failed

Save the `owner` and `owner_hash` for subsequent script calls.
If the user is not registered yet, register them first:

```bash
python ../authorize-user/scripts/register.py <username> <pin>
```

Username accepts both Cyrillic and Latin. "Давид" → "david" automatically via transliteration.

## Task File Format

```yaml
---
task_filename: "task-{timestamp}-{uuid}.md"
task_name: "..."
owner: "..."
owner_hash: "..."
created_at: "..."
status: active
global_objective: "..."
previous_context: "..."
current_task: "..."
---

{additional_context}
```

### Fields

| Field | Description |
|-------|-------------|
| `task_filename` | **The actual filename of this task file** — needed by agent for complete/continue operations |
| `task_name` | Short one-phrase name for user reference |
| `owner` | Authenticated username |
| `owner_hash` | SHA256 hash of user PIN — used to verify ownership |
| `created_at` | ISO timestamp of creation |
| `status` | `active` or `completed` |
| `global_objective` | Ultimate goal for deciding when the chain is DONE |
| `previous_context` | Condensed summary of prior steps |
| `current_task` | What to do right now |

Body: additional context, file paths, API docs, data samples, etc.

## Execution Protocol
## ⚠️ MANDATORY: Post-Task Completion Rule

**When you receive a task file as your first message, after executing `current_task`, you MUST do exactly ONE of the following — no third option exists:**

### Option A: COMPLETE the task
If the `global_objective` has been fully achieved (or the task is blocked and cannot proceed):
- Run `complete_task.py` with a report summarizing results
- This moves the file from `active/` to `completed/` for user review
- The lock file (`<filename>.lock`) is automatically removed

### Option B: CONTINUE the task chain
If more work is needed within the scope of `global_objective`:
- Run `create_task.py` with `--remove-parent-lock <current_task_filename>`
- This creates new task in `active/`, creates its `.lock` file, and removes the parent's `.lock`
- Include compressed `previous_context` and a concrete `current_task`

**You are NOT allowed to:**
- Execute the task and then do nothing
- Leave the task file in `active/` without calling either `complete_task.py` or `create_task.py`
- Report completion verbally without actually moving the file to `completed/`
- Abandon the task chain silently

**This rule applies to EVERY step in every task chain.** After executing `current_task`, the next action is always either complete or continue — without exception.


## Execution Steps

When you receive a task file as your first message:

1. **Load skill:** `load_skill("autonomous-tasks")`
2. **Parse frontmatter** — read ALL fields including `task_filename`
3. **Execute** the `current_task`
4. **Decide:** Has `global_objective` been achieved?

### COMPLETE (goal reached or blocked):

```bash
python scripts/complete_task.py \
  --filename "<task_filename_from_frontmatter>" \
  --report "Summary of accomplishments. Key outputs, file refs." \
  --owner-hash "<hash_from_auth>"
```

Moves file from `active/` to `completed/` with report. Lock file is automatically removed.
User will review it.

### CONTINUE (more steps needed):

```bash
python scripts/create_task.py \
  --owner "<owner_name>" \
  --owner-hash "<hash_from_auth>" \
  --task-name "Same or updated name" \
  --global-objective "Same objective" \
  --previous-context "Compressed summary of progress" \
  --current-task "Next concrete step" \
  --body "Details..." \
  --remove-parent-lock "<task_filename_from_frontmatter>"
```

The `--remove-parent-lock` flag tells the script to remove the current task's `.lock` file
after creating the new one. This ensures no race condition — the new task's lock is created
first, then the old one is removed.

Creates new task in `active/` with incremented step.


## User-Facing Workflows

### Workflow 1: Create a task

User: "Запланируй исследование рынка AI-ассистентов"

1. Parse user message — extract `username` and `pin`
2. Run `auth.py verify <username> <pin>`
3. If auth fails, tell user "PIN неверный"
4. If auth passes, collect:
  - `task_name` (one phrase, e.g. "Исследование рынка AI-ассистентов")
  - `global_objective` (full objective)
  - `current_task` (first step)
5. Create task with `create_task.py`
6. Confirm to user: "Задача создана: <task_name>. Вы увидите результат в списке задач."

### Workflow 2: Check task status

User: "Покажи мои задачи"

1. Run `auth.py verify <username> <pin>`
2. List tasks with `list_tasks.py --owner-hash <hash>`
3. Show user:
  - **Active tasks**: task_name, current_task
  - **Completed tasks**: task_name, completion_report, completed_at
  - **Processing tasks**: tasks with active lock files in `completed/`

### Workflow 3: Review and approve/reject a completed task

User sees completed task report. Ask for feedback.

**User approves (task done):**
```bash
python scripts/update_task.py \
  --action remove --filename "<filename>" --owner-hash "<hash>"
```

**User rejects (needs more work):**
```bash
python scripts/update_task.py \
  --action restore --filename "<filename>" --owner-hash "<hash>"
```

Then ask user what needs to be done.

## Context Compression Rules

For `previous_context` in next step:
1. **Concise** — 3-5 sentences max
2. **Keep critical info** — outputs, decisions, discoveries
3. **Drop noise** — no failed attempts, no intermediate states
4. **Include references** — note file paths of important outputs

Decision criteria:
- **COMPLETE** when `global_objective` fully achieved, output in final form
- **CONTINUE** when more steps needed within `global_objective` scope

## Important Notes

- **First message:** Always load this skill when receiving a task file
- **Authentication:** Always verify owner_hash before any task operation
- **Cross-user protection:** Users can only access their own tasks
- **Parallel chains:** Multiple independent task chains run simultaneously
- **Self-execution:** External system executes your tasks — do not self-run
- **Error handling:** On failure, create report in `completed/` explaining the issue
- **task_filename:** This field is auto-generated and placed in the task file frontmatter.
  Always use `task_filename` from the frontmatter when calling `complete_task.py` or `create_task.py --remove-parent-lock`.

## Authentication Delegation

This skill uses **authorize-user** for user identity verification. The agent should:
1. When user provides name + PIN pattern, call:
   `python ../authorize-user/scripts/verify.py <username> <pin>`
2. Save the returned `owner` and `owner_hash` for subsequent script calls
3. All task scripts use `owner_hash` for ownership verification

Do NOT implement your own PIN verification or store users separately.

