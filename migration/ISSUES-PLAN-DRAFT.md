# Open Issues Implementation Plan — merged design 기준 통합 실행 계획

작성일: 2026-08-18

이 문서는 오픈 이슈 15건과 Track 0(S-001~S-011)의 **실행 순서와 의존성**만 정리한다. 각 오픈 이슈의 설계는 이미 `main`에 병합된 canonical design을 source of truth로 사용하며, 이 문서에서 같은 결정을 다시 설계하지 않는다.

`AGENTS.md` rule 13은 계속 적용된다. 이 계획의 병합은 구현 승인이 아니다. 구현은 사용자가 해당 구현 범위를 명시적으로 승인한 뒤 시작한다.

## 범위

- Track 0: HANDOFF.md가 지시한 S-001~S-011 재설계 — design-only 유지
- Track P: 프로세스/에이전트/validator 하드닝 — #1, #2, #5, #6, #7, #8, #9, #11, #13, #14
- Track D: DB tooling — #18, #20, #21, #22, #23

현재 open 이슈 집합에 #19는 포함되지 않는다. 다만 #22의 legacy side-effect fixture 등에서 이미 설계된 외부 선행조건으로 참조될 수 있다.

## 계획 원칙

1. **이슈 본문보다 merged canonical design이 우선한다.** 이슈 작성 당시 전제가 이후 설계 PR에서 수정된 경우 반드시 현재 `main`의 설계를 따른다.
2. **설계 재개방 금지.** 구현 중 새로운 lock-in 결정이 필요해지면 임의 결정하지 않고 해당 design gate를 다시 연다.
3. **논리 의존성과 파일 merge 순서를 구분한다.** 서로 독립적인 작업도 같은 validator/agent/skill 파일을 건드리면 순차 merge한다.
4. **공통 contract를 먼저 구현하고 leaf 전파를 나중에 한다.** artifact schema, durable state, routing/role boundary, DB connection/safety가 공통 기반이다.
5. **YAGNI 유지.** 현재 feature가 요구하지 않는 범용 abstraction, 추가 migration history, always-on DB infra는 만들지 않는다.

## Canonical design source

| 이슈 | 구현 source of truth | 현재 판단 |
|---|---|---|
| #1 | `docs/08-feature-artifact-validation.md` | 설계 병합 완료, 구현 대기 |
| #2 | `docs/issue-2-artifact-schema-validation.md` | #1 위의 static schema layer |
| #5 | `docs/10-command-execution-contract.md` | durable state contract 소비 |
| #6 | `docs/10-skill-execution-contract.md` | #5/#7/#8 ownership/routing 보존 |
| #7 | `docs/09-agent-skill-routing.md` | phase + primary artifact 기반 routing |
| #8 | `docs/10-agent-role-boundary.md` | path-granular designer permission 적용 |
| #9 | `docs/09-evidence-grade-transition-control.md` | revision-aware transition 검사 |
| #11 | `docs/03-evidence-and-verification.md`, `docs/templates/verification.md`, `migration/RULEBOOK.md` | effective judge self-check 필수 |
| #13 | `docs/11-stop-condition-contract.md` | STOP payload/routing/OQ 처리 |
| #14 | `docs/11-durable-state-protocol.md` | STATE/QUEUE/generation의 canonical contract |
| #18 | `docs/issue-18-mssql-readonly-inspection.md` | `mssql-prod-ro` 전용 catalog inspection |
| #20 | `docs/12-db-execution-safety-contract.md` | runtime attestation + capability boundary |
| #21 | `docs/13-postgresql-test-db-and-schema-migration.md` | Alembic Adopt 완료; runtime bootstrap만 Defer |
| #22 | `docs/issue-22-db-snapshot-diff-contract.md` | feature-scoped delta parity contract |
| #23 | `docs/12-db-connection-secrets-contract.md` | canonical profile/resolver contract |

## Track P — 구현 의존성

### P-A: feature artifact / validator lane

`#1 -> #2 -> #9`

- **#1 먼저**: `feature-card.md`의 canonical `id/stage/blocked`, stage별 필수 artifact, synthetic-demo 정규화, validator 구조를 먼저 구현한다.
- **#2 다음**: #1 parser/structure 위에 enum/ID/scope/reference validation을 올린다. body `Status:` 같은 두 번째 lifecycle source를 만들지 않는다.
- **#9 다음**: #2와 parser/constants를 공유할 수 있지만 grade promotion 판단은 반드시 explicit base revision을 받는 별도 revision-aware checker로 유지한다.

PR 53 기존안의 `#2 -> #1` 순서는 반대로 수정한다.

### P-S: durable state / command / STOP lane

`#14 -> (#5, #13)`

- **#14 먼저**: STATE/QUEUE frontmatter, canonical queue table, legal transition, blocker/dependency syntax, shared `generation`, ordered write/recovery를 한 세트로 구현한다. enum만 부분 적용하지 않는다.
- **#5**: command argument/precondition/output 계약을 #14의 exact state transitions에 연결한다. `migration-status`는 read-only로 유지한다.
- **#13**: STOP 원인/payload/OQ dedupe/routing은 #13 계약을 따르고, 실제 QUEUE/STATE persistence는 #14 contract만 사용한다. read-only specialist가 shared state를 직접 수정하게 만들지 않는다.

#5와 #13은 논리적으로 병렬 가능하지만 coordinator/validator 관련 변경이 겹치면 순차 merge한다.

### P-R: routing / permission / skill lane

`(#7, #8) -> #6 -> #11`

- **#7**: agent/skill 선택을 phase + primary artifact 기반으로 명시하고 normal return과 gate-blocking STOP을 구분한다.
- **#8**: `migration-designer`는 deny-by-default + `target-feature-design.md` 예외만 허용하고, `task: deny`를 포함해 implementation proxy를 차단한다.
- **#6**: #5 command ownership, #7 routing, #8 permission boundary를 소비해 skill별 exact inputs/outputs/branches를 반영한다. skill이 STATE/QUEUE/lifecycle을 독자 갱신하지 않는다.
- **#11**: 단순 `where practical` 삭제가 아니다. effective judge configuration fingerprint, mandatory negative control, reuse 조건, verification artifact 기록, BLOCKED 처리, regression test까지 한 구현 단위로 적용한다.

#11은 #6과 `parity-verification` 파일이 겹치므로 #6 이후 merge하는 것을 기본으로 한다.

### Track P merge 권장 순서

1. #1
2. #2
3. #14
4. #7, #8
5. #5
6. #13
7. #6
8. #9
9. #11

#9는 #2 이후 언제든 병렬 구현 가능하다. 위 순서는 주로 shared-file 충돌을 줄이기 위한 merge 순서다.

## Track D — 구현 의존성

### D-F: connection / execution safety foundation

`#23 -> #20`

- **#23 먼저**: canonical logical profiles는 정확히 `mssql-prod-ro`, `mssql-test-rw`, `postgres-test-rw`이다. env keys는 `MSSQL_PROD_RO_CONN`, `MSSQL_TEST_RW_CONN`, `PG_TEST_RW_CONN`을 사용한다. raw connection string/임의 env-var 입력 경로를 추가하지 않는다.
- `.gitignore`의 `.env` 보호는 이미 존재하므로 불필요하게 다시 설계하거나 중복 설정하지 않는다.
- **#20 다음**: profile label을 safety proof로 사용하지 않는다. 실제 연결 후 engine/server/database identity를 attestation하고, `ReadOnlySession`/`TestWriteSession` capability를 분리하며 unknown/mismatch는 fail-closed한다.
- keyword-only guard, `--force`/`--unsafe`, production RW profile은 금지한다.

### D-I: MSSQL inspection

`#23 + #20 -> #18`

- `scripts/db/mssql_inspect.py`는 `mssql-prod-ro`만 허용한다.
- V1은 fixed catalog `SELECT` allowlist 기반 `snapshot`에 한정한다.
- arbitrary SQL, DDL/DML, `EXEC`, SP/job 실행, application row export는 범위 밖이다.
- JSON을 canonical capture로 두고 raw definitions/job text는 기본적으로 non-Git local artifact로 보관한다.

### D-C: DB snapshot/diff

`#23 + #20 -> #22 core`, 이후 live adapter integration에서 `#18` 및 실제 fixture 준비 상태와 join

#22를 #18 전체 완료 뒤에만 시작하도록 직렬화하지 않는다.

먼저 DB 비의존 core를 구현할 수 있다.

- canonical typed JSON / digest
- compatible snapshot pairing
- `delta` (`added/removed/updated`)
- raw-value-free `render`
- stable key / hard `max_rows` / deterministic ordering validation
- staged snapshot/delta synthetic mutation negative-control

그 뒤 read-only `capture`와 `DbAssertionPort` adapter를 #20 guard에 연결한다. live MSSQL integration은 #18이 준비된 뒤 연결하고, legacy side-effect fixture / PostgreSQL fixture는 해당 환경이 실제로 준비된 시점에 연결한다.

범용 ORM/자유형 comparison language/물리 schema 자동 동등성 비교는 만들지 않는다.

### D-P: PostgreSQL bootstrap

#21은 **Alembic 선택을 Defer하는 이슈가 아니다.** Alembic은 이미 PostgreSQL schema history의 단일 source로 Adopt 완료됐다.

현재 Defer 대상은 실제 `scripts/db/pg_test_bootstrap.py`와 disposable PostgreSQL test target/runtime wiring이다. 첫 PostgreSQL schema-changing feature가 필요로 할 때 승인된 feature scope 안에서 구현한다.

그 시점에는:

- `postgres-test-rw` + #20 attested `TestWriteSession`을 사용하고
- Alembic head를 적용하며
- clean reset/seed identity를 evidence로 남기고
- persistent `app` DB나 일반 `DATABASE_URL`을 destructive reset target으로 재사용하지 않는다.

### Track D merge 권장 순서

1. #23
2. #20
3. #18과 #22 core 병렬 구현 가능
4. #22 capture/adapter live integration
5. #21 runtime bootstrap은 실제 schema-changing feature까지 Defer

## Track 0 — S-001~S-011 재설계

Track 0은 HANDOFF.md 지시대로 계속 **design-only**다. Track P/D 구현 계획과 별도 gate로 관리한다.

다만 기존 문서의 “파일 충돌 없음” 가정은 제거한다. Track 0은 `migration/RULEBOOK.md`, `docs/02-*`, `docs/03-*`, ADR 등 shared design surface를 수정할 수 있으므로 다른 브랜치와 의미/파일 충돌이 생길 수 있다.

병렬 작업 자체는 가능하지만 각 merge 직전 최신 `main` 기준으로 rebase/review하고, 이미 병합된 canonical issue design을 되돌리지 않는지 확인한다.

## 통합 마일스톤

| 마일스톤 | 범위 | 완료조건 |
|---|---|---|
| M0 | 이 계획 정합성 확정 | PR plan이 merged canonical design과 일치 |
| M1 | P:#1/#14, D:#23 foundation | 각 이슈 acceptance criteria + 관련 테스트 통과 |
| M2 | P:#2/#7/#8/#5, D:#20 | shared schema/state/routing/safety contract 구현 완료 |
| M3 | P:#13/#6/#9, D:#18 + #22 core | leaf propagation 및 DB core tooling 구현 완료 |
| M4 | P:#11, D:#22 live adapter/integration | parity judge/self-check 및 DB comparison 경로 연결 |
| M5 | #21 runtime bootstrap | 첫 실제 PostgreSQL schema-changing feature에서만 수행 |

Track 0은 M0~M5와 독립된 design-only 흐름이며, shared-file 충돌 때문에 merge 직전 최신 main 재검토가 필수다.

## 구현 시작 전 체크

각 이슈 구현을 시작하기 전에 다음을 확인한다.

1. 해당 이슈의 canonical design 문서를 읽었는가.
2. 이슈 본문의 stale recommendation을 그대로 구현하지 않는가.
3. 선행 contract가 실제 `main`에 구현되어 있는가.
4. 구현 범위가 issue acceptance criteria를 넘어서지 않는가.
5. 새 lock-in 결정이 생기면 design gate를 다시 열도록 되어 있는가.
6. shared file을 수정하는 다른 작업과 merge 순서가 정해져 있는가.

## 검증/완료 기준

- 각 이슈는 자신의 merged design 및 issue implementation comment의 acceptance criteria를 만족해야 한다.
- `scripts/validate_scaffold.py` 및 관련 targeted tests를 실행한다.
- DB tooling은 secret redaction, fail-closed identity/capability checks, raw artifact non-Git 기본값을 검증한다.
- state tooling은 generation/invariant/partial-write recovery를 검증한다.
- agent/skill/command 변경은 routing, permission, persistence ownership을 서로 침범하지 않는지 회귀 검증한다.
- parity path는 effective configuration negative control이 성공하기 전에는 PASS를 허용하지 않는다.

## 명시적 비고

- 이 문서의 merge는 구현 승인으로 해석하지 않는다.
- 이미 merged된 설계를 다시 “설계 대기” 상태로 돌리지 않는다. 구현 중 충돌이나 신규 결정이 발견될 때만 해당 design gate를 재개방한다.
- Critical/High 우선순위보다 **dependency safety와 shared-contract 선행**을 우선한다.
- #21의 runtime bootstrap은 YAGNI 원칙에 따라 실제 필요 시점까지 Defer한다.
