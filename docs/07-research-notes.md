# Research Notes

Last reviewed: 2026-08-15

This file records the external material that informed the initial scaffold. It is not a claim that every referenced tool should be installed.

## OpenCode

### Agent Skills

Source: https://opencode.ai/docs/skills/

Relevant points:

- project skills live under `.opencode/skills/<name>/SKILL.md`;
- skills are discovered by the native `skill` tool;
- project-level skills can carry project-specific reusable procedures;
- permissions can restrict skill access per agent.

### Agents

Source: https://opencode.ai/docs/agents/

Relevant points:

- project custom agents can be defined under `.opencode/agents/`;
- Markdown frontmatter supports description, mode, model, temperature, permissions, and other agent settings;
- this enables read-only analyzer/reviewer roles and write-capable implementer roles.

### Commands

Source: https://opencode.ai/docs/commands/

Relevant points:

- project commands live under `.opencode/commands/`;
- Markdown command files can select an agent and accept `$ARGUMENTS`;
- commands provide stable operator entry points for repeatable pipeline stages.

### Rules / AGENTS.md

Source: https://opencode.ai/docs/rules/

Relevant points:

- `AGENTS.md` is a project-level instruction source and is intended to be committed to Git;
- `/init` can generate/update it based on repository structure, build/test commands, and conventions.

### Config / permissions

Sources:

- https://opencode.ai/docs/config/
- https://opencode.ai/docs/permissions/

Relevant points:

- project config is stored in `opencode.json`;
- plugins can be loaded from the `plugin` array;
- edit/bash/task/skill permissions can be controlled explicitly;
- compaction and watcher behavior are configurable.

## Superpowers

Source: https://github.com/obra/superpowers/blob/main/docs/README.opencode.md

Relevant points:

- OpenCode is directly supported;
- installation can use `superpowers@git+https://github.com/obra/superpowers.git` in `opencode.json`;
- it maps its workflow concepts onto OpenCode native tools;
- project skills under `.opencode/skills/` take precedence over generic Superpowers skills.

## Anthropic large-scale migration process

Sources:

- https://claude.com/blog/ai-code-migration
- https://github.com/anthropics/code-migration-kit-with-claude-code

Relevant ideas adopted here:

- establish an exit condition/judge before mass migration;
- invest early in a migration Rulebook;
- use a pilot before broad conversion;
- separate implementer and adversarial reviewer roles;
- keep work queues mechanical and resumable on disk;
- use build/test/parity failures as work queues;
- fix the process/rules when the same defect pattern recurs.

Important adaptation: this project is not a same-architecture language port. WPF -> React/FastAPI and MSSQL -> PostgreSQL changes architecture and deployment boundaries, so the migration unit is a business feature rather than a source file.

## Bun Zig -> Rust case

Source: https://claude.com/blog/introducing-dynamic-workflows-in-claude-code

The case demonstrated large-scale parallel agent work with independent reviewers and iterative build/test repair. The useful lesson for this project is the workflow structure, not file-for-file translation.

## Community recommendation page

Starting reference from the project discussion:

- https://leankim.xyz/community/recommend

The page was used as an ecosystem discovery starting point. Final choices in this repository are based on fit with OpenCode and the migration constraints, not on recommendation count alone.
