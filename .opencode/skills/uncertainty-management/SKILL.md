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

## Inputs

- The artifact or evidence that exposed the unanswered material question.
- [Input] `migration/features/<feature-id>/feature-card.md` and the feature artifact that needs a resumable local update, when the question is feature-scoped.
- [Input] `docs/05-open-questions.md` and the existing OQ registry, including any matching ID.
- [Input] The resolved scope: feature-local, cross-feature/project-wide, DLL/host, deployment, security, or policy.
- [Input] Current evidence and grade/provenance references; an unknown is not answered by assigning `?` alone.

## Outputs

- [Output] A feature-local update request for `migration/features/<feature-id>/feature-card.md` when the unknown affects only that feature.
- [Output] A project/cross-feature update request for `docs/05-open-questions.md` when the unknown affects multiple features, DLL/host behavior, deployment, security, or global policy.
- [Output] The exact question, impact, evidence/grade, resolution path, OQ-### ID, and blocking/provisional state.
- For a read-only invoking role, return complete update bodies and canonical destinations to `migration-coordinator`; do not write a duplicate question into both destinations. The coordinator may cross-reference one OQ ID in both when required.
- This skill never updates `migration/STATE.md`, `migration/QUEUE.md`, feature lifecycle metadata, or an unrelated behavior/design artifact.

## Procedure

1. [Input] Read the exposing artifact/evidence, `migration/features/<feature-id>/feature-card.md` when feature-scoped, and `docs/05-open-questions.md` before creating or updating an entry.
2. [Input] State the exact unanswered question and identify the artifact, gate, confidence, or design decision it affects.
3. [Input] Record current evidence, provenance, grade, and the cheapest realistic resolution path; do not turn an inference into a confirmed answer.
4. [Output] Choose one destination: feature-local `migration/features/<feature-id>/feature-card.md` for a single-feature unknown, or project-wide `docs/05-open-questions.md` for cross-feature/global scope.
5. [Output] Assign or update one `OQ-###` ID, preserve existing references, and return the complete update body plus blocking/provisional classification to `migration-coordinator`.
6. [Input] Re-check that the question is neither duplicated with a divergent copy nor silently removed because a likely answer exists.

## Branches

- If the exposing artifact, scope, or current evidence is missing, return `BLOCKED`; do not invent the question's answer or a destination.
- If the unknown affects only one feature, return a feature-card update request for `migration/features/<feature-id>/feature-card.md` and keep the project registry referenceable by OQ ID.
- If the unknown affects multiple features, DLL/host behavior, deployment, security, or global policy, route it to `docs/05-open-questions.md`; do not force it into one feature card.
- If current evidence conflicts, preserve both sides, record the conflict in the OQ entry, and return `PARTIAL` or `BLOCKED`; never select the convenient account silently.
- If the unknown does not block the current gate, record it as provisional and return `PARTIAL` so unaffected work may continue.
- If the unknown blocks a medium/high lock-in decision or verification, return `BLOCKED`, stop that decision, and wait for evidence or a human gate rather than guessing.
- If an OQ-### entry already exists, update or cross-reference it in place; never create a divergent duplicate or an alternate canonical file.
- `BLOCKED` and `PARTIAL` are skill result labels. The common STOP payload, durable state, queue status, and lifecycle transition remain coordinator-owned.

## Done means

Every material unknown encountered by the scoped work has one exact OQ-### record or a feature-card update request with explicit impact, evidence/grade, resolution path, and blocking/provisional state. The canonical update is persisted by an authorized role or handed to `migration-coordinator`, and no answer was guessed.
