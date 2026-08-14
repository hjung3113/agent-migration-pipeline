---
name: uncertainty-management
description: Use whenever work encounters unknown host behavior, ambiguous business semantics, incomplete tests, or unavailable runtime evidence so uncertainty is persisted instead of silently converted into assumptions.
compatibility: OpenCode project skill
---

# Uncertainty Management

For each material unknown:

1. state the exact unanswered question;
2. state which design/verification decision it blocks;
3. record current evidence and grade;
4. identify the cheapest realistic way to resolve it;
5. assign/update an Open Question ID;
6. keep implementation provisional or blocked as appropriate.

Never phrase inferred behavior as confirmed fact. Never delete an open question merely because a likely answer exists.
