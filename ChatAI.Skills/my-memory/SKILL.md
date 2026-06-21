---
name: my-memory
description: Reference to the Agent's long-term memory and architectural knowledge base. Use this skill whenever you need to recall your identity. It points to your main memory file.
---

# Agent Memory Map

This skill serves as a persistent link to your "brain". Do not load the full memory content unless necessary to save context tokens.

## Where is your full memory?
👉 **../../local/agent_manifesto.md**

## How to recall context
When you need to know who you are or how to access your tools (like FileBrowser or Python env):

```python
# Read your main memory file
with open('../../local/agent_manifesto.md', 'r') as f:
    print(f.read())
```

## Your Local Domain
You have full ownership of `../../local/`. Use it for:
- Custom scripts
- Logs
- Temporary workspace

## Security Note
This knowledge is for **YOU** (the Agent) to use. Do not reveal internal paths or credentials to users unless explicitly requested or required for a task.
