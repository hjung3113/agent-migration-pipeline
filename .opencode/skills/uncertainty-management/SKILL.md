---
name: uncertainty-management
description: Primary skill when work encounters an unanswered material question whose resolution affects a decision, gate, or confidence; the primary artifact is a tracked open-question entry (exact question, impact, evidence, resolution path, blocking state); do not use as the primary skill for grading an existing claim or hiding an unknown behind a `?` without tracking the question.
compatibility: OpenCode project skill
---

# Uncertainty Management

## Primary artifact boundary

Invoke this as the **primary skill** only when work encounters an **unanswered material question** whose resolution affects a decision, gate, or confidence. The primary artifact is the open-question entry: exact question, impact, evidence, resolution path, blocking/provisional state (persisted in `docs/05-open-questions.md` with an `OQ-###` ID).

Do not use this as the primary skill for:

- grading a resolved/existing claim — `evidence-grading` owns the grade and evidence record;
- hiding an unknown behind `?` without tracking the question — an evidence record must not pretend to answer an open question;
- synthesizing the feature contract — `behavior-contract` owns it (and may invoke this skill as a supporting skill for its unresolved-items section).

## Skill tie-break

When more than one skill appears applicable:

1. identify the artifact the current step is required to produce or update;
2. select the skill that owns that primary artifact;
3. invoke supporting skills only for their narrower sub-output;
4. return all outputs to the primary agent/coordinator; do not let a supporting skill silently change phase or scope.

Worked example: the question is "does the host invoke this callback on the UI thread?" and no evidence exists — use this skill; the output is an open question, not an evidence record pretending to answer it.

For each material unknown:

1. state the exact unanswered question;
2. state which design/verification decision it blocks;
3. record current evidence and grade;
4. identify the cheapest realistic way to resolve it;
5. assign/update an Open Question ID;
6. keep implementation provisional or blocked as appropriate.

Never phrase inferred behavior as confirmed fact. Never delete an open question merely because a likely answer exists.
