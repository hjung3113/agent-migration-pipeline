# Agent Migration Pipeline

OpenCode 기반으로 레거시 애플리케이션을 웹 아키텍처로 점진 전환하기 위한 **에이전트 마이그레이션 환경 초안**입니다.

현재 대상 프로젝트의 기준은 다음과 같습니다.

- Legacy: C# WPF + MSSQL
- Target frontend: TypeScript + React + Tailwind CSS
- Target backend: Python + FastAPI
- Target database: PostgreSQL
- Host integration: 사내 플랫폼이 현재 DLL 형태의 라이브러리를 호출
- Constraint: 실제 화면 관찰이 제한적이며 기존 자동 테스트가 완전하지 않음

따라서 이 저장소는 소스 파일을 기계적으로 번역하는 방식이 아니라, **업무 기능과 관찰 가능한 동작을 먼저 복원하고 Feature 단위로 재설계/구현/검증**하는 파이프라인을 지향합니다.

## Core principles

1. **Behavior over source parity** — C# 구조를 그대로 옮기지 않고 입력, 처리 규칙, 출력, DB 변경, callback, file/log 등 관찰 가능한 동작을 기준으로 합니다.
2. **Evidence over guessing** — 테스트가 부족한 부분은 코드, 실행 결과, DB 변화, 로그, 수동 확인을 증거로 남기고 신뢰도를 구분합니다.
3. **Feature over file** — 마이그레이션 단위는 `.cs` 파일이 아니라 업무 Feature/Vertical Slice입니다.
4. **Platform boundary isolation** — DLL/플랫폼 종속성은 adapter boundary로 격리합니다.
5. **Independent review** — 구현 에이전트와 리뷰/검증 에이전트를 분리합니다.
6. **Disk-backed state** — Rulebook, queue, evidence, open questions를 저장소 파일로 유지하여 세션이 바뀌어도 이어갈 수 있게 합니다.
7. **Fix the process** — 반복되는 오류는 개별 코드보다 Rulebook/Skill/검증 루프를 먼저 수정합니다.

## Pipeline

```text
Legacy C# / WPF / MSSQL / DLL boundary
                  |
                  v
          [Legacy Discovery]
                  |
       Feature + dependency map
                  |
                  v
        [Behavior Contract]
                  |
      Evidence + confidence grade
                  |
                  v
          [Human Gate where needed]
                  |
                  v
        [Target Feature Design]
                  |
        React / FastAPI / PostgreSQL
                  |
                  v
            [Implementer]
                  |
                  v
       [Adversarial Reviewer]
                  |
                  v
             [Verifier]
       /       |       |       \
 tests   DB diff   output diff  manual evidence
                  |
            PASS / FAIL
                  |
          FAIL -> rule/process fix
```

## OpenCode setup

OpenCode project-local conventions are used directly:

- `AGENTS.md`: project-wide agent rules
- `.opencode/agents/`: specialized agents
- `.opencode/skills/`: reusable migration skills
- `.opencode/commands/`: repeatable pipeline commands
- `opencode.json`: project config and Superpowers plugin

Superpowers is included as a supporting workflow plugin. Migration-specific rules in this repository remain authoritative for this project.

### Suggested start

```text
1. Clone repository
2. Start OpenCode in repository root
3. Confirm Superpowers plugin loads
4. Read docs/00-project-context.md
5. Resolve high-priority items in docs/05-open-questions.md
6. Run /migration-discover against the legacy repository when available
```

## Custom commands

- `/migration-discover <scope>` — legacy feature/dependency discovery
- `/migration-spec <feature>` — behavior contract + evidence grading
- `/migration-design <feature>` — target web architecture design
- `/migration-implement <feature>` — implement an approved feature design
- `/migration-review <feature>` — independent adversarial review
- `/migration-verify <feature>` — parity/evidence verification
- `/migration-status` — summarize queue, evidence, risks, and unresolved questions

## Repository map

```text
.
├── AGENTS.md
├── opencode.json
├── .opencode/
│   ├── agents/
│   ├── commands/
│   └── skills/
├── docs/
│   ├── adr/
│   └── templates/
├── migration/
│   ├── RULEBOOK.md
│   ├── STATE.md
│   ├── QUEUE.md
│   ├── features/
│   └── evidence/
└── scripts/
```

## Current status

This repository is a **Phase 0 scaffold**. No legacy source has been analyzed yet. Unknown facts are intentionally recorded rather than filled with assumptions. See [`docs/05-open-questions.md`](docs/05-open-questions.md).

## Research basis

The structure is informed by OpenCode's native Agents/Skills/Commands model, Superpowers' OpenCode integration, and Anthropic's published large-scale migration workflow. Detailed notes and source links are in [`docs/07-research-notes.md`](docs/07-research-notes.md).
