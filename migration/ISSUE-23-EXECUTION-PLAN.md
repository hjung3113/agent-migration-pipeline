# Issue #23 실행 계획 — DB connection profile resolver + secret injection contract 구현

작성일: 2026-08-24
기준 커밋: `b0ea736` (= `origin/main`, 본 워크트리 `hjung3113/issue23-plan` 분기점)
Canonical design: `docs/12-db-connection-secrets-contract.md` (병합 커밋 `35ff26b` 이후
본문 무변경 확인 — `git diff 35ff26b main -- docs/12-db-connection-secrets-contract.md`
빈 출력). 본 계획은 이 문서를 재설계하지 않고 구현만 계획한다.
상위 계획: `migration/ISSUES-PLAN-DRAFT.md` — Track D 레인 전체(`#23 -> #20`,
`#23 -> #18`, `#23 + #20 -> #22`)의 root이자 Track D merge 순서 1번
이슈 본문: GitHub Issue #23 "[DB-Tooling][High] DB 자격증명/연결 설정 관리 규약 부재"
(본문 권고 일부 stale — 게이트 2 참조)

이 문서는 (1) ISSUES-PLAN-DRAFT "구현 시작 전 체크" 7항목을 현재 `main` 기준으로
재확인한 결과와 (2) #23 구현의 실행 계획(DAG)을 담는다. 이 문서 자체는 구현이
아니며, 구현 승인 절차를 대체하지 않는다. **이미 병합된 `docs/12` 계약을 재설계·
재개방하지 않는다** — 남은 범위는 그 계약이 명시한 "Later implementation shape"
6개 항목 + acceptance criteria의 최소 구현이다.

구현 범위 요약(설계 L181–192 + 본 세션 지시): ① `.env.example` 3개 빈 canonical
key ② `scripts/db/` 하부 공유 connection-profile resolver(fixed registry + fail-closed
lookup + secret redaction) ③ driver/연결 코드 없음 — #18/#20/#22가 나중에 소비
④ `scripts/validate_scaffold.py` 최소 확장(.env.example 3 key 존재·빈 값 + `.gitignore`
보호 유지 확인) ⑤ focused tests(unknown profile / unset env / empty-whitespace env /
forbidden profile-tool combo / no-secret error rendering) ⑥ 금지 항목 준수(4번째
profile, prod-RW profile, config-file 입력, raw connection string CLI, dotenv
auto-loading 전부 불가).

---

## 1. 게이트 체크 결과 (7항목 전부 확인, 블로커 없음)

모든 확인은 문서 예시가 아니라 현재 `main`(=본 브랜치 HEAD `b0ea736`)의 실제 파일
기반이다. 이 시점의 기본 상태(본 세션 실행으로 확인): `python3
scripts/validate_scaffold.py` exit 0, `python3 -m pytest scripts/tests/ -q` —
404 passed, `check_doc_links.py` / `check_oq_updates.py` green, open PR 없음
(`gh pr list` 빈 결과).

### 게이트 1 — canonical design 문서를 읽었는가 → 통과

`docs/12-db-connection-secrets-contract.md`(210줄) 전문을 읽고 현재 `main`과
대조했다. 설계의 "Current repository facts"(L19–24) 전제를 전부 실재 파일로
재검증했다:

| 설계 전제 | 실재 확인(`b0ea736`) |
|---|---|
| `.gitignore`이 `.env`/`.env.*` 무시 + `!.env.example` 재허용 (L21) | `.gitignore` L11–13에 정확히 `.env` / `.env.*` / `!.env.example` 순서로 존재(negation이 패턴 뒤에 있어 유효) |
| `.env.example` 없음 (L22) | 존재하지 않음(`ls .env*` 매치 없음) |
| OQ-021(legacy DLL 설정 메커니즘) OPEN, 이 계약과 별개 (L23, L36) | `docs/05-open-questions.md` L47 `OQ-021 | OPEN` — 이 이슈로 상태 바꾸지 않음 |
| `scripts/db/` 하부 resolver 없음 (L186) | `scripts/db/` 디렉터리 자체가 없음. `scripts/` = validator 4개 + `tests/`뿐. #18/#21/#22 설계가 예약한 `scripts/db/mssql_inspect.py` 등도 아직 없음 |
| #18–#22가 profile 어휘를 공유해야 함 (L24) | 소비 도구 부재 — #23이 어휘의 최초·유일 구현체가 됨(충돌 대상 없음) |

설계의 fail-closed 5조건(L78–82), 금지 CLI 입력 5종(L60–66), secret 불변식
(L88–107), `.env.example` canonical payload(L113–117), 구현 형태 6항목
(L183–190), acceptance criteria(L196–206), Non-goals(L208–210)를 구현 판정의
근거로 그대로 사용한다(§3, §6 매핑).

### 게이트 2 — 이슈 본문의 stale recommendation을 그대로 구현하지 않는가 → 통과

이슈 #23 본문 대비 확정된 차이 (merged canonical design이 우선, 계획 원칙 1):

| 이슈 본문 권고 | 현재 설계의 판정 | 구현 시 지침 |
|---|---|---|
| `.env.example` **또는** `config/db_connections.example.json` 신설 | 설계가 config-file 경로를 명시적으로 거부(Adversarial finding 1: 병립 파일 기반 구성 경로가 우연한 secret 소스가 됨). L60–66도 "paths to secret-bearing connection config files"를 금지 CLI 입력으로 열거 | `.env.example`만 생성. `config/` 디렉터리·JSON 예시 파일 생성 금지 |
| `.gitignore`에 `.env`, `.env.*`, `config/db_connections.json` 추가 확인/추가 | 규칙은 이미 존재(게이트 1). 설계 L125: "implementation should not churn `.gitignore` unless … additional secret-bearing local path" — 현 구현은 신규 secret 경로를 만들지 않으므로 무변경. `config/db_connections.json` 항목은 거부된 경로이므로 추가하지 않음 | `.gitignore` 무변경. 대신 validator가 기존 3규칙의 존재·순서를 지속 강제(T-2) |
| `docs/06-tooling-decisions.md`에 결정 기록 | 이미 되어 있음 — `docs/06:78–90`("DB connection and secret injection contract" 절)이 env-var 전용·profile 이름만 수용·prod-RW 부재·fail-closed·OQ-021 독립을 요약하고 `docs/12`를 canonical로 지시. 본문 권고는 병합된 설계 작업으로 이미 충족 | `docs/06` 무변경 |
| 4개 DB 도구 이슈(#18–#22)에 규약 참조 추가 | 설계 "Tool-specific consumption"(L127–158)이 소비 규칙을 이미 소유. 설계 Non-goals(L208): "change Issues #18-#22 implementation" — #23은 어휘를 제공만 하고 소비 배선은 각 이슈가 수행 | #18/#20/#22 파일·문서 무변경. resolver를 소비 가능한 형태로 제공하는 것으로 충족(§6의 이후-소비 항목 참조) |
| 환경변수명 `MSSQL_PROD_RO_CONN`/`MSSQL_TEST_RW_CONN`/`PG_TEST_RW_CONN` | 설계 L42–46 표와 정확히 일치 — drift 없음 | 그대로 사용 |
| "지금은 규약과 예시 파일만, 실제 값 주입은 이후" | 설계 구현 형태와 일치 — driver/연결 코드 없이 profile resolution + secret injection 계약만 구현 | 연결 코드·드라이버 금지(Non-goals) |

본문의 문제 진단(자격증명 관리 규약 부재 → 모든 DB 도구의 선행 기반)은 설계가
그대로 승계했고 Track D root 배치로 반영됐다. stale 본문을 그대로 따르는 항목은
없다.

### 게이트 3 — 선행 contract가 실제 main에 구현되어 있는가 → 통과

#23은 Track D merge 순서 1번 — 선행 이슈가 없다. 대신 설계가 전제하는 저장소
기반이 실재하는지 확인했다:

| 전제 요소 | 위치(`b0ea736`) | 확인 내용 |
|---|---|---|
| `.gitignore` 보호 규칙 | `.gitignore` L11–13 | 설계 L21 전제 그대로. `git check-ignore` smoke는 T-I1에서 실행 |
| validator 확장 기반 | `scripts/validate_scaffold.py` (2,628줄) | additive `validate_*()` 함수 패턴 선례(#5/#7/#8/#13/#14/#6), 상수 블록(L834–905 인근), `main()` errors 통합(L2607), root 파라미터 관례(`validate_features`, `validate_command_contract`) |
| 스크립트 import 기반 | `scripts/tests/conftest.py` | repo root를 sys.path에 추가 — `scripts.*` 네임스페이스 패키지 import 가능(`scripts/__init__.py` 불요, 현행 관례). `scripts/db/`도 동일 관례 적용(§3 P-1) |
| 기존 `.env` 관련 검사 | 없음 | `validate_scaffold.py`에 `.env` 관련 검사 부재 — 신규 추가가 기존 검사와 충돌하지 않음 |
| pytest 기반 | `scripts/tests/` 11개 파일, 404 passed | 신규 테스트 파일 추가만으로 참여(컨벤션: `test_*.py`, 파일별 단위 도메인) |

Track P(#1–#14)는 전부 병합 완료(HANDOFF 2026-08-24: "Track P is done"). #23이
의존하는 다른 contract는 없다.

### 게이트 4 — 사용자의 명시적 구현 승인 → 조건부 통과 (이번 세션은 구현 없음)

- `AGENTS.md` rule 13 (design gate) 유효.
- HANDOFF.md 최신 항목(`b0ea736`, 2026-08-24): "**Rule-13 Track P/D authorization
  remains in effect and has not been revoked.**" + "Before starting #23, redo the
  '구현 시작 전 체크' 7-item gate against current `main`" — 본 세션 지시가 바로
  그 게이트 재실행 + 실행 계획 작성이다. Track P 전 이슈(#1/#2/#14/#7/#8/#5/#13/
  #6/#9/#11)에서 동일 standing authorization이 issue-by-issue 구현의 근거로
  연속 적용됐다.
- ISSUES-PLAN-DRAFT 원칙: "이 계획 문서 또는 PR의 merge만으로 승인됐다고 간주하지
  않는다." **본 실행 계획 문서 자체가 구현 승인이 아니다.** 본 세션 지시는
  "게이트 체크 + 실행 계획 문서 + 커밋"으로 한정되어 있으므로 **본 세션에서는
  구현 코드를 작성하지 않는다.** 구현 세션은 standing authorization과 이 게이트
  결과가 green임을 재인용한 뒤 착수한다.
- 게이트 결과에 블로커가 없으므로 별도 승인 질의 항목은 없다.

### 게이트 5 — 구현 범위가 acceptance criteria를 넘지 않는가 → 통과

범위 상한 = 설계 "Later implementation shape" 6개 항목(L183–190) + "Acceptance
criteria"(L196–206) + 본 세션 지시가 명시한 6개 항목(위 요약과 동일). 구체적으로:

- 변경/신규: `.env.example`(신규), `scripts/db/connection_profiles.py`(신규),
  `scripts/tests/test_db_connection_profiles.py`(신규),
  `scripts/validate_scaffold.py`(신규 독립 검사 함수 + 상수 추가),
  `scripts/tests/test_env_example_contract.py`(신규), `HANDOFF.md`(T-H1).
- 비변경(Non-goals): `docs/12-db-connection-secrets-contract.md`(canonical),
  `.gitignore`(게이트 2), `docs/06-tooling-decisions.md`(이미 기록), OQ-021 상태,
  Issues #18–#22의 파일·문서, DB driver/연결 코드·의존성 추가(pydbc/psycopg/
  sqlalchemy 등 전부 금지 — 표준 라이브러리만 사용), dotenv 의존성·auto-load,
  config-file 입력 경로, raw connection string CLI 입력, 4번째 profile·prod-RW
  profile, CI workflow 변경, 다른 validator 섹션 무관 영역(본 세션 지시: "do not
  touch unrelated validator sections").

### 게이트 6 — 새 lock-in 결정 시 design gate 재오픈 근거 → 통과

재오픈 메커니즘이 3중으로 존재: ISSUES-PLAN-DRAFT 계획 원칙 2("설계 재개방 금지.
구현 중 새로운 lock-in 결정이 필요해지면 임의 결정하지 않고 해당 design gate를
다시 연다"), AGENTS.md rule 13, 본 계획 §5의 명시적 트리거. 특히 "profile 추가는
runtime 옵션이 아니라 design change"(L53)이므로 §5 트리거 2를 구현 세션에 전달한다.

### 게이트 7 — shared file merge 순서 → 통과

- `gh pr list` open PR 없음(본 세션 확인). 본 브랜치 = `origin/main`(`b0ea736`)
  분기 직후, 커밋 없음.
- 로컬 잔존 브랜치 `hjung3113/issue9-followup`, `hjung3113/issue13-stop-condition`:
  squash-merge 이전의 stale 분기(PR #66 / #13 — 내용은 이미 `main`에 병합,
  `git log main..` 로 확인되는 커밋은 pre-squash 사본). #23 파일과 교집합 없음
  (issue9-followup는 grade-transition 파일, issue13-stop-condition의
  validate_scaffold 변경도 이미 main에 반영됨). 작업 대상 아님.
- `scripts/validate_scaffold.py` 충돌 패턴: #23은 기존 함수 내부 확장(#9/#11)이
  아니라 **신규 독립 함수 additive 추가**(#5/#7/#8/#13/#14/#6 선례) — `main()`의
  errors 통합 지점 1줄만 공유하므로 충돌 창이 최소다. 해당 파일을 수정하는 다른
  진행 중 작업이 없으므로(위 확인) 순차 단일 PR이면 충돌 없음.
- Track D 후속(#20/#18/#22)은 #23 merge 이후에만 착수(Track D merge 순서) —
  `scripts/db/` 소유권 경합도 없다.
- HANDOFF(`b0ea736`)의 PR #67 교훈 — **"freshly written validators in this repo
  keep under-enforcing their own declared column/field sets on the first pass"** —
  가 #23의 T-2(신규 validator)와 T-R1(리뷰)에 직접 적용된다. 독립 리뷰 종료 후
  소유자 수준 2차 패스를 DAG에 명시적으로 예산화한다(§4 T-R1/T-H1).

---

## 2. 현재 구현 기준선 (구현 세션이 기대해야 하는 출발 상태)

### `.gitignore` (L11–13)

```gitignore
.env
.env.*
!.env.example
```

이 순서(negation이 `.env.*` 뒤)가 유효한 보호 상태다. T-2 validator가 이 3규칙
존재 + 순서를 강제하고, T-I1이 `git check-ignore`로 경험적으로 확인한다.

### `scripts/` 구조

`scripts/db/` 없음. `scripts/` = `check_doc_links.py`, `check_oq_updates.py`,
`sync_agent_stop_conditions.py`, `validate_grade_transition.py`,
`validate_scaffold.py`, `tests/`. `scripts/__init__.py` 없음 — `scripts.tests/conftest.py`가
repo root를 sys.path에 넣어 네임스페이스 패키지로 import(`from scripts.validate_scaffold
import …`). `scripts/db/`도 `__init__.py` 없이 동일 관례(§3 P-1).

### `scripts/validate_scaffold.py` (2,628줄)

- 상수 블록: L834–905(A-2 enum/regex), L858–887(#11 judge self-check 상수) — 신규
  상수도 관련 없는 영역 침범 없이 인접 배치 선례에 따름.
- 집계: `collect_validation_errors()`(L2593, feature artifact/durable state/STOP
  영역 담당) ← `main()`(L2607)이 routing/skill-execution 계약 검사와 함께 errors
  리스트 통합. 신규 repo-guard 성격 검사는 `main()` 체인에 직접 추가(§3 P-4).
- 진단 형식 관례: `path:line [category] message`.
- 동작 baseline: exit 0.

### 테스트 기반

`scripts/tests/` 11개 파일, 404 passed. 관례: 도메인별 파일 분리(#9가 validator
신규 영역을 `test_grade_history.py` 신규 파일로, #11이 내용계약을
`test_judge_self_check_contract.py` 신규 파일로), validator 테스트는 `tmp_path`
합성 fixture repo 패턴(`test_validate_scaffold.py:make_repo` 선례) + 실제 저장소
green 확인 1개. pytest는 로컬/리뷰 회귀용(CI `repo-guards`는 validator +
doc-links + OQ만 실행 — #9/#11과 동일).

### 문서 정합

`docs/06:78–90`이 이 계약의 결정 요약 + `docs/12` canonical 지시를 이미 기록.
`docs/01:73`이 #18 도구의 `mssql-prod-ro` 소비를 예고. 참조 변경 불필요.

---

## 3. 파생 판정 사항 (신규 lock-in 아님 — 근거 명시)

구현 중 아래 판정은 임의 결정이 아니라 병합된 `docs/12`에서 유도된다.
구현자/리뷰어가 유도 근거에 동의하지 않으면 그때만 design gate를 재오픈한다.

- **P-1. Resolver = 단일 모듈 `scripts/db/connection_profiles.py`, `__init__.py`
  없음.** 근거: 설계 L186 "one shared DB connection-profile resolver under
  `scripts/db/`" — 파일명은 설계가 못 정한 구현 자유이며, 소비 도구(#18
  `mssql_inspect.py`, #21 `pg_test_bootstrap.py`, #22 `db_snapshot_diff.py` — 각
  설계가 이미 파일명 예약)와 구별되는 공유 모듈 이름으로 `connection_profiles`를
  선택. `scripts/`가 `__init__.py` 없는 네임스페이스 패키지 관례(conftest 기반)이므로
  `scripts/db/`도 동일 관례를 따른다(신규 packaging 도입 안 함). 모듈명이 곧
  어휘의 단일 source가 되므로 #18–#22는 `from scripts.db.connection_profiles
  import resolve_connection_profile, PROFILES`로 소비한다.
- **P-2. 공개 API 형태 — profile 이름 단일 위치 인자 + keyword-only 가드 3인자,
  예외는 메타데이터만 운반.** 근거: 설계 L58("DB tools receive only a logical
  profile selector")·L68("resolves the fixed environment-variable mapping
  internally")로 입력 표면을 profile 이름으로 제한; fail-closed L80("a tool
  requests a profile outside its explicit allowlist")·L82("a write-capable
  operation requests a profile whose declared capability is read-only")가
  `allowed_profiles`/`operation` 파라미터의 존재 이유. 표준 라이브러리
  (`dataclasses`, `os`, `typing`)만 사용 — driver/dotenv 금지(L70, L192,
  Non-goals). 정확한 인터페이스는 §4 T-1에 코드로 명시. `operation="read"`는
  최소권한 기본값이며 write 도구는 `operation="write"`를 명시 전달해야 한다(해석
  여지 없는 caller intent 선언 — SQL 수준 쓰기 강제는 #20 소유, L86).
- **P-3. `.env.example` 내용 = canonical payload + profile 메타데이터 한 줄 주석.**
  근거: L113–117이 payload를 `KEY=` 3줄로 고정하고, L121–122가 "comments may
  explain profile purpose but must not include production-looking hosts, usernames,
  passwords, tokens, or realistic secret examples"를 허용/금지한다. 주석은
  profile 이름·engine·environment·capability(docs/12 표의 공개 메타데이터)와
  `docs/12` 포인터로 한정한다. 정확한 파일 내용은 §4 T-1에 전문 명시.
- **P-4. Validator 확장 = 신규 독립 함수 `validate_env_example_contract()` additive
  추가 + `main()` 체인 직접 배선.** 근거: 기존 함수 내부 확장(#9/#11)과 달리 이번
  검사는 기존 어떤 `validate_*()`의 발견 범위(feature 디렉터리, skills, agents,
  durable state)에도 속하지 않는 repo-guard 성격이다 — additive 독립 함수가
  #5/#7/#8/#13/#14/#6 선례와 일치. `collect_validation_errors()`는 feature
  artifact/durable-state/STOP 집계기(docstring)이므로 여기에 넣지 않고
  `main()`의 errors 통합에 routing 계약 검사들과 나란히 추가한다. root
  파라미터(`root: Path | None = None`)는 `validate_features` 선례로 tmp_path
  테스트를 가능하게 한다. "Extend only enough … do not touch unrelated validator
  sections"(본 세션 지시) 준수.
- **P-5. Validator 강제 수위 — key 집합 정확 일치 + RHS 엄격히 빈 값 + `.gitignore`
  3규칙 존재·순서. 주석 내용은 기계 검사하지 않음.** 근거: acceptance L200
  ("`.env.example` contains only empty canonical keys" — "only"가 extra key 금지,
  "empty"가 빈 RHS 요구)와 L201("secret-bearing `.env` variants remain ignored" —
  무시 규칙의 존속이 검사 대상)에서 직접 유도. `.gitignore`은 3규칙 존재 +
  `!.env.example`의 index가 `.env.*`의 index보다 뒤인지까지 확인한다(gitignore
  부정 규칙은 이후 규칙이 이전을 무효화하므로 순서가 보호의 실질). 반면 주석의
  "realistic-looking 값" 탐지는 휴리스틱 과경화다 — 설계는 주석을 허용(L121)하며
  HANDOFF PR #67 교훈(신규 validator의 초회 과소/과잉경화)에 따라 리뷰(T-R1)로
  검사한다. 이 수위를 넘는 검사는 §5 트리거 7.
- **P-6. 테스트 배치 — 신규 파일 2개로 T-1/T-2 파일 소유권 완전 분리.**
  `scripts/tests/test_db_connection_profiles.py`(resolver 단위 테스트)와
  `scripts/tests/test_env_example_contract.py`(validator 테스트). 근거: 도메인별
  파일 분리 관례(#9의 `test_grade_history.py`, #11의
  `test_judge_self_check_contract.py` 선례). `test_validate_scaffold.py`는 docstring이
  A-1 feature-artifact 전용, `test_validate_schema.py`는 A-2 영역이므로 둘 다
  확장하지 않는다. 이 배치가 병렬 그룹 A(§4)의 충돌 없는 병렬성을 만든다.
- **P-7. CLI 엔트리포인트 없음 — import 전용 모듈.** 근거: 설계가 예약한 소비자는
  #18/#20/#22의 도구들이며(L187–188) 현재 소비자가 없다. standalone CLI
  (`python -m scripts.db.connection_profiles …`)는 요구되지 않은 실행 표면을
  하나 더 만들 뿐이고(YAGNI), 값을 출력하는 경로가 늘어나면 redaction 불변식의
  검증 대상도 늘어난다. 필요해지면 그때 #20 이후 설계에서 추가.
- **P-8. 오류 메시지 문형 = 설계 L105 패턴 준수.** "Logs and errors may say
  `MSSQL_PROD_RO_CONN is not set`; they must not include the value" — 모든
  fail-closed 오류는 ① env var **이름**(설정되지 않음/비었음), ② profile 이름,
  ③ 허용 목록/알려진 profile 목록, ④ `.env.example`/`docs/12` 안내 중 비밀이 아닌
  것만 포함한다. 환경변수 전체 dump·driver 진단·사례가 담긴 명령 예시 금지(L107).
  구조적 보장: 예외 객체 생성 코드 경로에 env value 문자열이 들어가지 않도록
  생성자에서 메타데이터만 조립하고, 테스트가 모든 오류 경로에 대해 sentinel 값
  부재를 단언한다(§4 T-1 테스트 8).
- **P-9. `.gitignore` 무변경 + `config/*` 항목 미추가.** 근거: 게이트 2 표 — 설계
  L125가 구현 도입 신규 secret 경로가 없는 한 churn 금지, config-file 경로는
  finding 1로 거부됐으므로 그 ignore 항목도 존재 근거가 없다. 보호 지속성은
  validator(T-2)와 `git check-ignore` smoke(T-I1)로 확인한다.
- **P-10. `docs/06` 무변경.** 근거: 게이트 2 — 이슈 본문의 "docs/06에 결정 기록"
  권고는 `docs/06:78–90`(병합된 설계 작업)로 이미 충족됐다. #23 구현이 문서
  결정을 다시 기록하면 이중 source가 된다.

---

## 4. 태스크 분해 (DAG)

원칙: T-1(resolver + `.env.example` + 단위 테스트)과 T-2(validator 확장 + 테스트)는
파일이 완전 분리되어 병렬 가능하다. 물리적으로는 **단일 브랜치/단일 PR**로
출하한다(§7).

```text
T-0 (완료: 이 문서) 게이트 체크 + 실행 계획
     |
     v
[병렬 그룹 A]  T-1 ∥ T-2   (파일 완전 분리)
     |
     v
T-I1 통합 검증 (validator + 전수 pytest + doc links/OQ + git check-ignore smoke)
     |
     v
T-R1 독립 adversarial review (구현자와 독립, AGENTS.md rule 10)
     |     + 소유자 수준 2차 패스 예산화 (HANDOFF PR #67 교훈 — 신규 validator 초회 과소강제 패턴)
     v
T-H1 HANDOFF.md 갱신 + Issue #23 구현 코멘트 + PR 개설(merge는 사용자 명시 지시 대기)
```

### T-1 — connection-profile resolver + `.env.example`

**대상 파일**: `.env.example`(신규), `scripts/db/connection_profiles.py`(신규),
`scripts/tests/test_db_connection_profiles.py`(신규). 선행: T-0.

`.env.example` 전문(P-3):

```dotenv
# Migration DB connection profiles — canonical contract:
# docs/12-db-connection-secrets-contract.md
# Values are opaque connection strings injected via the process environment.
# Never commit real values (secret-bearing .env variants are git-ignored).

# mssql-prod-ro: MSSQL / production / read-only (legacy schema inspection)
MSSQL_PROD_RO_CONN=

# mssql-test-rw: MSSQL / test / read-write (test sync destination)
MSSQL_TEST_RW_CONN=

# postgres-test-rw: PostgreSQL / test / read-write (target bootstrap/parity)
PG_TEST_RW_CONN=
```

`scripts/db/connection_profiles.py` 공개 인터페이스(P-1/P-2/P-8):

```python
"""Canonical DB connection-profile registry and fail-closed resolver.

Contract: docs/12-db-connection-secrets-contract.md (Issue #23).
No DB drivers, no connections — profile resolution and secret
injection contract only. Issues #18/#20/#22 consume this module.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Collection, Mapping

ENGINE_MSSQL = "mssql"
ENGINE_POSTGRESQL = "postgresql"
ENVIRONMENT_PRODUCTION = "production"
ENVIRONMENT_TEST = "test"
CAPABILITY_READ_ONLY = "read-only"
CAPABILITY_READ_WRITE = "read-write"
OPERATIONS = ("read", "write")


@dataclass(frozen=True)
class ConnectionProfile:
    name: str       # logical profile name, e.g. "mssql-prod-ro"
    env_var: str    # fixed environment-variable name, e.g. "MSSQL_PROD_RO_CONN"
    engine: str
    environment: str
    capability: str


PROFILES: Mapping[str, ConnectionProfile] = {
    profile.name: profile
    for profile in (
        ConnectionProfile("mssql-prod-ro", "MSSQL_PROD_RO_CONN",
                          ENGINE_MSSQL, ENVIRONMENT_PRODUCTION, CAPABILITY_READ_ONLY),
        ConnectionProfile("mssql-test-rw", "MSSQL_TEST_RW_CONN",
                          ENGINE_MSSQL, ENVIRONMENT_TEST, CAPABILITY_READ_WRITE),
        ConnectionProfile("postgres-test-rw", "PG_TEST_RW_CONN",
                          ENGINE_POSTGRESQL, ENVIRONMENT_TEST, CAPABILITY_READ_WRITE),
    )
}


class ProfileResolutionError(Exception):
    """Raised before any connection attempt. Message carries only
    non-secret metadata (profile name, env-var NAME, capability) —
    never the environment-variable value."""


@dataclass(frozen=True)
class ResolvedProfile:
    profile: ConnectionProfile
    connection_value: str


def resolve_connection_profile(
    profile_name: str,
    *,
    allowed_profiles: Collection[str] | None = None,
    operation: str = "read",
    environ: Mapping[str, str] | None = None,
) -> ResolvedProfile:
    """Resolve a logical profile to its connection value, fail-closed.

    Raises ProfileResolutionError (before any connection attempt) when:
    the profile is unknown; the profile is outside this tool's allowlist;
    the operation is not one of OPERATIONS; a write operation targets a
    read-only profile; the mapped env var is unset; or it is empty or
    whitespace-only. No fallback, no aliasing, no default database.
    """
```

구현 요구:

- fail-closed 검사 순서(설계 L78–82 + goal 4의 malformed 입력): ① unknown
  profile → ② `allowed_profiles` 위반 → ③ invalid `operation` → ④ `operation
  == "write"` × `capability == read-only` → ⑤ env var unset → ⑥ env var
  empty/whitespace. 전부 값을 읽기 전·연결 시도 전에 오류.
- 오류 문형(P-8): 예 — unknown: ``unknown connection profile 'X'; known
  profiles: mssql-prod-ro, mssql-test-rw, postgres-test-rw (see
  docs/12-db-connection-secrets-contract.md)`` / forbidden: ``connection
  profile 'X' is not allowed for this tool; allowed profiles: …`` / write-RO:
  ``connection profile 'mssql-prod-ro' declares capability 'read-only';
  write operations are forbidden`` / unset: ``MSSQL_PROD_RO_CONN is not set
  (connection profile 'mssql-prod-ro'); populate the environment — see
  .env.example`` / empty: ``MSSQL_PROD_RO_CONN is empty or whitespace-only
  (connection profile 'mssql-prod-ro')``.
- `environ=None`이면 `os.environ` 사용(테스트 주입용 선택 인자 — DB 도구는
  기본값만 사용).
- registry는 모듈 상수로 고정 — runtime 등록·변경 API 없음(L53: profile 추가는
  design change).

테스트(`test_db_connection_profiles.py`) — 설계 L190 item 6 + 본 세션 지시 5항:
1. registry 고정: `PROFILES` key 집합이 정확히 3개, 각 profile의
   name/env_var/engine/environment/capability가 docs/12 L42–46 표와 정확 일치.
2. **prod-RW 부재**: environment=production ∧ capability=read-write인 profile이
   registry에 존재하지 않음(acceptance L205).
3. 정상 해결: read × `mssql-prod-ro`, write × `mssql-test-rw`, write ×
   `postgres-test-rw` — `ResolvedProfile.connection_value`가 주입한 값과 일치.
4. unknown profile 오류(존재하지 않는 이름).
5. env var unset 오류 — 메시지에 env var **이름** 포함.
6. env var empty(`""`) / whitespace-only(`"   "`) 오류.
7. forbidden 조합: `allowed_profiles={"mssql-prod-ro"}` 상태에서
   `mssql-test-rw` 요청 오류.
8. **no-secret error rendering**: 모든 오류 케이스(4–7)에 대해 environ에
   sentinel 값(예: `"mssql://user:SECRET-VALUE@host.example:1433/db"`)을 심고
   `str(exc)`·`exc.args` 전체에 sentinel·`SECRET-VALUE` 부재 단언(acceptance
   L203, 설계 L105).
9. invalid `operation`(예 `"admin"`) 오류.

### T-2 — `validate_scaffold.py` 최소 확장

**대상 파일**: `scripts/validate_scaffold.py`,
`scripts/tests/test_env_example_contract.py`(신규). 선행: T-0.

- 신규 상수(L858–887 인근): `ENV_EXAMPLE_PATH = ".env.example"`,
  `ENV_EXAMPLE_KEYS = ("MSSQL_PROD_RO_CONN", "MSSQL_TEST_RW_CONN",
  "PG_TEST_RW_CONN")`, `GITIGNORE_ENV_RULES = (".env", ".env.*",
  "!.env.example")`.
- 신규 독립 함수 `validate_env_example_contract(root: Path | None = None) ->
  list[str]`(P-4/P-5), 진단 형식 `path:line [env-example] message` 관례:
  - E1: `.env.example` 존재 부재 오류.
  - E2: `KEY=` 라인 파싱(주석 `#`·빈 줄 제외) — key 집합이 `ENV_EXAMPLE_KEYS`와
    **정확히 일치**(missing·extra 모두 오류).
  - E3: 각 key의 RHS가 엄격히 빈 값 — `KEY=` 뒤에 무엇이든(whitespace 포함)
    있으면 오류.
  - E4: `.gitignore`에 `GITIGNORE_ENV_RULES` 3규칙 존재 +
    `!.env.example`의 라인 index > `.env.*`의 라인 index(부정 규칙 유효 순서).
- 배선: `main()`의 errors 통합 튜플에 추가(기존 검사·섹션 무변경).
- 테스트(`test_env_example_contract.py`, `tmp_path` 합성 fixture 패턴):
  존재하지 않는 파일(E1), key 누락·추가 key(E2), 값 있는 RHS·whitespace RHS(E3),
  `.env`·`.env.*` 규칙 제거·`!.env.example`를 `.env.*` 앞으로 이동한 `.gitignore`
  (E4), 정당한 파일(주석 포함 — 설계 L121 허용) green, 실제 저장소 대상 green
  (T-1의 `.env.example`·현행 `.gitignore` 통과).

### T-I1 — 통합 검증

- `python3 scripts/validate_scaffold.py` exit 0(신규 검사가 기존 전 검사와 공존).
- `python3 -m pytest scripts/tests/ -q` 전수 통과(404 baseline + 신규).
- `check_doc_links.py`, `check_oq_updates.py` green(OQ-021 상태 무변경 포함).
- `.gitignore` 보호 smoke: `git check-ignore -q .env` exit 0,
  `git check-ignore -q .env.local` exit 0, `git check-ignore -q .env.example`
  exit 1(무시되지 않음).
- 비범위 무변경 확인: `git diff`로 `.gitignore`·`docs/12`·`docs/06`·#18–#22 관련
  파일 무변경; `scripts/db/`에 driver/dotenv import 부재
  (`pyodbc|psycopg|sqlalchemy|dotenv|pymysql` grep).
- 미달 시 수정 후 재실행.

### T-R1 — 독립 adversarial review (구현자와 독립, AGENTS.md rule 10)

§6 완료 기준 대조. 특히:

- (a) **PR #67 교훈 적용 — 과소강제 점검**: E2가 subset만 검사해 extra key를
  놓치는지, E3가 whitespace를 허용하는지, E4가 규칙 존재만 보고 순서(부정 규칙
  무효화)를 놓치는지. 독립 리뷰 종료 후 **소유자 수준 2차 패스**를 한 번 더
  실행(HANDOFF 명시 패턴 — 세 번 반복된 신규 validator 초회 결함 계열).
- (b) **secret 누출 탐색**: 모든 오류 경로·traceback에서 env value 부재(T-1
  테스트 8의 보완으로 리뷰어가 변형 케이스 시도 — 예: profile 이름에 값을 넣어
  호출해도 echo는 입력 자기자신일 뿐 env 비밀이 아님을 확인).
- (c) **Non-goals/금지 준수**: 4번째 profile·prod-RW·config-file 경로·raw conn
  CLI·dotenv auto-load·driver 연결 코드 전부 부재; 표준 라이브러리 외 의존성
  부재; `.gitignore`·`docs/12`·`docs/06` 무변경.
- (d) **stale 본문 부활 부재** (게이트 2 표): `config/db_connections*`,
  docs/06 신규 기록, #18–#22 파일 수정이 없는지.
- (e) validator가 무관 섹션(A-1/A-2/durable state/STOP/skill/routing)을 건드리지
  않았는지 — 추가된 것은 상수 + 독립 함수 + `main()` 1줄뿐인지.

발견 사항은 수정 후 re-verify.

### T-H1 — HANDOFF 갱신 + Issue 코멘트 + PR

- `HANDOFF.md` in-place 갱신: 근거 SHA·테스트 수·resolver 소비 안내
  (`from scripts.db.connection_profiles import …`)·잔여 불확실성(§6 이후-소비
  항목) 포함.
- Issue #23에 구현 코멘트(게이트 결과 요약 + acceptance 매핑).
- PR 개설 + 리뷰 코멘트 게시 후 **사용자의 명시적 merge 지시 대기**
  (2026-08-22 워크플로 변경, #65/#66/#67 선례). merge 직전 `git log
  <base>..HEAD` 재확인(#13 세션 타이밍 레이스 선례). merge 후 소유자 post-merge
  리뷰가 끝나기 전에는 #23을 완료로 간주하지 않는다(#61/#62/#64/#65/#67 선례).

병렬성 요약: 그룹 A(T-1/T-2)는 파일 소유권 완전 분리로 병렬 가능. 단일 세션 실행
시 순서 권장: T-1 → T-2(실제 `.env.example`가 먼저 있으면 T-2의 실제-저장소
green 테스트가 즉시 성립) → T-I1.

---

## 5. 설계 게이트 재오픈 트리거 (구현 중 하나라도 걸리면 중단하고 기록)

1. **실제 연결·driver 코드 필요성 발견.** acceptance를 만들기 위해 연결이
   필요하다고 판명되면 Non-goals 위반이다 — 임의로 추가하지 않고 게이트 재개방.
2. **금지 형태에 대한 요구 발생.** 4번째 profile 추가(L53: design change),
   production read-write profile(L52), config-file 입력 경로(finding 1), raw
   connection string CLI(finding 2), dotenv 의존성·auto-load(L70) — 어느 하나가
   필요해 보이는 순간 #23 범위를 벗어난 신규 설계 질문이다.
3. **현행 `.gitignore` 규칙의 보호 공백 발견.** 구현이 도입한 신규
   secret-bearing 로컬 경로가 생기는 경우에만(L125의 유일한 churn 허용 조건)
   `.gitignore` 변경을 설계에 붙여 질의한다.
4. **OQ-021 해결이 이 계약에 영향을 주어야 한다는 주장.** 설계 L36이 독립성을
   계약 조건으로 못 박았다 — legacy DLL 메커니즘 관찰은 OQ-021로 기록만 한다.
5. **#18/#20/#22 소화 관점에서 resolver API 부족 발견.** API 확장(신규 파라미터,
   신규 프로필 속성 등)은 신규 lock-in이다 — 임의 확장 금지, 해당 이슈 설계와
   함께 재개방.
6. **이슈 본문 권고 부활 유혹** (게이트 2): `config/db_connections.example.json`,
   docs/06 재기록, #18–#22 파일 직접 수정.
7. **P-5의 검사 수위를 넘는 validator 요구.** 예: 주석에서 realistic credential
   휴리스틱 탐지, `.env.example` 이외 파일 스캔 확장 — canonical이 못 박지 않은
   과경화는 PR #67 교훈상 리뷰로 충분한지 먼저 판단하고, 기계화가 필요하면
   별도 승인.

재개방 시 취할 행동: 해당 design gate(#23 또는 충돌하는 타 이슈 설계)을 열고
`docs/05-open-questions.md` 또는 이슈 코멘트로 미결정 사항을 기록한 뒤 사용자
판단을 기다린다. 임의 결정 금지.

---

## 6. 검증/완료 기준

설계 acceptance criteria(L196–206) → 구현 매핑:

| 설계 완료 기준 | 담당 |
|---|---|
| 3개 canonical profile이 고정 env var로만 해결 (L197) | T-1 registry + 테스트 1/3 — 임의 env var 이름 입력 경로 자체 부재(P-2 입력 표면) |
| 어떤 migration DB 스크립트도 raw 자격증명/연결 문자열을 CLI로 받지 않음 (L198) | 구조적 만족 — DB 스크립트는 resolver뿐이며 resolver 입력은 profile 이름만(P-2); T-R1 (c) 확인 |
| `.env.example`이 빈 canonical key만 포함 (L199–200) | T-1 파일 + T-2 E2/E3 상시 강제 |
| secret-bearing `.env` 변형이 계속 무시됨 (L201) | `.gitignore` 무변경(P-9) + T-2 E4 상시 강제 + T-I1 `git check-ignore` smoke |
| missing/unknown/forbidden 구성이 연결 수립 전 실패 (L202) | T-1 fail-closed 5조건 + 테스트 4–7 — 연결 코드 자체가 없어 구조적으로 "연결 전" |
| 연결 값이 로그·오류·evidence·커밋 파일에 절대 등장하지 않음 (L203) | T-1 테스트 8(redaction) + P-8 문형 + T-R1 (b) — evidence 산출물도 없음(연결 없음) |
| #18–#22가 동일 resolver/profile 어휘 사용 (L204) | **이후-소비 기준**: #23은 어휘·모듈을 제공(P-1)하고 소비 배선은 각 이슈 범위에서 달성 — 본 이슈 완료 판정에서 "소비 대기"로 명시적 표기(Non-goals L208) |
| tooling registry에 production read-write 부재 (L205) | T-1 테스트 2 |
| OQ-021은 legacy DLL 메커니즘 실제 관찰 전까지 계속 OPEN (L206) | T-I1 OQ 체크 green + 무변경 |

추가 완료 기준:

- `python3 scripts/validate_scaffold.py` exit 0 — 신규 검사가 기존 검사
  전부와 공존.
- `python3 -m pytest scripts/tests/ -q` 전수 통과(404 baseline + 신규).
- `check_doc_links.py`, `check_oq_updates.py` 통과.
- 독립 리뷰(T-R1) + 소유자 2차 패스가 Non-goals 위반·과소강제·secret 누출·
  stale 권고 부활을 발견하지 않음.
- Issue #23은 merge(사용자 명시 지시 후) + 소유자 post-merge 리뷰 완료 전까지
  완료로 간주하지 않는다.

## 7. PR/merge 권장

**단일 PR 권장.** T-1(계약 실체)과 T-2(그 불변식의 상시 강제)는 하나의 계약
결합부다 — 분리 시 "canonical key가 존재해야 한다고 선언된 시점 + 강제하지 않는
validator" 혼합 상태가 발생한다(본 저장소 "no mixed-contract state" 선례,
#5/#6/#9/#11). 파일 수도 작다(`.env.example` + resolver 1 + validator 1 + 테스트
2 + HANDOFF).

merge 순서: Track D 1번 항목. #23 merge 전에 #20/#18/#22 착수 금지(Track D merge
순서). 진행 중 병렬 브랜치 없음(open PR 없음 확인). 구현 브랜치는 최신 `main`에서
분기해 단일 PR로 squash-merge하되, **PR 개설 + 리뷰 코멘트 게시 후 사용자의
명시적 merge 지시를 기다린다**(2026-08-22 워크플로 변경, PR #65/#66/#67 선례).
merge 직전 `git log <base>..HEAD` 재확인.
