# Issue #20 실행 계획 — DB execution safety guard (db_guard + connectors) 구현

작성일: 2026-08-24
기준 커밋: `44949a5` (= `origin/main`, 본 워크트리 `hjung3113/issue20-plan` 분기점,
diff 0 확인)
Canonical design: `docs/12-db-execution-safety-contract.md` (병합 커밋 `cf81318`,
이후 본문 무변경 확인 — `git diff cf81318 HEAD -- docs/12-db-execution-safety-contract.md`
빈 출력). 본 계획은 이 문서를 재설계하지 않고 구현만 계획한다.
Authoritative dependency: `docs/12-db-connection-secrets-contract.md` (Issue #23) —
구현체 `scripts/db/connection_profiles.py`를 현재 `main` 그대로 소비한다
(`resolve_connection_profile`, `PROFILES`). **주의: 이 파일은 #23 실행계획이 제안한
모양에서 리뷰 2회(`19cf39f`, `ac8a231`)를 거쳐 변경됐다** — `MappingProxyType` 고정
레지스트리, `allowed_profiles`/`operation`/`environ` keyword-only 파라미터, 오류
메시지의 caller 입력 에cho 회피. 계획은 현재 파일 기준(HANDOFF 지시).
상위 계획: `migration/ISSUES-PLAN-DRAFT.md` — D-F 레인 `#23 -> #20`, Track D merge
순서 2번. 상위 계획 L102는 #20 구현이 `docs/issue-19-mssql-test-materialization.md`
(#19, CLOSED·미구현)의 materialization 개념에 실제 의존하게 되면 조용히 넘기지
말고 별도 확인하라고 명시 — §1 말미에서 판정하고 §5 트리거 1로 유지한다.
이슈 본문: GitHub Issue #20 "[DB-Tooling][Critical] 위험 DB 동작(INSERT/UPDATE/EXEC)을
테스트 DB로만 강제 라우팅하는 안전장치 부재" (본문 권고 일부 stale — 게이트 2 참조)

이 문서는 (1) ISSUES-PLAN-DRAFT "구현 시작 전 체크" 7항목을 현재 `main` 기준으로
재확인한 결과와 (2) #20 구현의 실행 계획(DAG)을 담는다. 이 문서 자체는 구현이
아니며, 구현 승인 절차를 대체하지 않는다. **이미 병합된 `docs/12` 안전 계약을
재설계·재개방하지 않는다** — 남은 범위는 그 계약의 "Implementation acceptance
criteria" 13개 항목 + "Failure behavior" 표 전 행의 최소 구현이다.

구현 범위 요약: ① `scripts/db/db_guard.py` — 공개 경계
`open_readonly` / `open_test_readwrite` → `ReadOnlySession` / `TestWriteSession`
(Layer 4 capability API, 11단계 실행 흐름 L204–216) ② `scripts/db/connectors/` —
engine별 driver + identity probes (L343–349 구조, Layer 3) ③ expected-target
비밀 아닌 안전 메타데이터 레지스트리 (L113–118, L120 "minimal repository/config
representation") ④ Layer 5 6-class 연산 분류기 — 보수·fail-closed, SQL parser
아님(Non-goals L427) ⑤ 구조화 audit event + redaction (L289–320) ⑥ 직접
DB-driver import 차단 CI/정적 검사 (L336–355, acceptance 12) ⑦ 테스트 전수는
fake 기반 — 실제 production mutation은 결코 테스트 케이스로 쓰지 않는다 (L421).
비범위: #18/#19/#21/#22 도구 구현(L430), 프로필/비밀 경로 변경(#23 소유),
`--force`류 우회로(L322–334), 실제 DB 연결이 필요한 통합 검증(승인된 테스트
인프라가 생긴 뒤).

---

## 1. 게이트 체크 결과 (7항목 전부 확인, 블로커 없음)

모든 확인은 문서 예시가 아니라 현재 `main`(=본 브랜치 HEAD `44949a5`)의 실제 파일
기반이다. 이 시점의 기본 상태(본 세션 실행으로 확인): `python3
scripts/validate_scaffold.py` exit 0, `python3 -m pytest scripts/tests/ -q` —
434 passed, `check_doc_links.py` / `check_oq_updates.py` green, open PR 없음
(`gh pr list` 빈 결과).

### 게이트 1 — canonical design 문서를 읽었는가 → 통과

`docs/12-db-execution-safety-contract.md`(436줄) 전문을 읽고 현재 `main`과
대조했다(병합 커밋 `cf81318` 이후 무변경). 구현 판정의 근거로 사용하는 절과 줄:

| 설계 요소 | 근거 줄 |
|---|---|
| adversarial findings 1–11 (키워드 차단 불충분, 이름만의 신뢰 금지, 유사성 경고 ≠ 경계, raw SQL 로깅 금지, 우회로 부재, 직접 driver import 차단…) | L24–34 |
| 권한 경계 — #23이 profile/injection 소유, #19가 materialization 의미론 소유, #20이 runtime 실행 안전 소유 | L47–56 |
| 다층 신뢰 모델 (server policy → #23 profile → attestation → capability API → 분류/audit → approved connector) | L62–81 |
| Layer 1 — 서버단 least privilege가 1차 방어선, guard가 쓰기로 read-only를 검증하는 것 금지 | L83–97 |
| Layer 2 — canonical 3 profile 표, expected_target 메타데이터, "minimal repository/config representation / 두 번째 비밀 경로 금지", 거부 조건 6개, unknown/malformed → fail-closed | L99–131 |
| Layer 3 — 접속 후 engine/server/database identity attestation, 불일치·probe 실패·timeout → 차단, production read도 attestation 필수, 유사성 진단은 승인 규칙 아님 | L133–158 |
| Layer 4 — `open_readonly`/`open_test_readwrite` capability API, raw connection/cursor 비노출, capability API가 곧 권한 경계 | L160–175 |
| Layer 5 — 6-class 표(read/mutation/ddl/procedure-exec/privileged/unknown), batch 최대 위험 계승, unknown 포함 batch 강등 금지, 주석/공백/대소문자/순서 불변, rollback 포장 강등 금지 | L177–198 |
| 필수 실행 흐름 11단계 — 1–9단계 실패 시 driver는 위험 문장을 받지 않음 | L200–218 |
| production read-only 허용/금지 목록, 잘못된 권한 계정에서도 guard는 차단 | L220–240 |
| test read-write — canonical `test + read-write` + attestation 뒤에만, `privileged`는 계속 거부 | L242–251 |
| #18/#19/#21/#22/#23 소비 관계 (#19는 source=ReadOnlySession, target=TestWriteSession 고정) | L253–287 |
| audit 계약 — 필드 최소 집합, 금지 로그(비밀/파라미터/row 값/PII literal), stable hash | L289–320 |
| no-bypass 계약 — `--force`/`--unsafe`/확인 프롬프트/env 무효화/unknown 강등 플래그/raw connection 전부 금지 | L322–334 |
| repository 구조상 우회 방지 — `scripts/db/db_guard.py` + `connectors/` 스케치, CI/AST 검사, 열거式 예외(파일명/의도 추론 금지), FastAPI persistence 층은 자동 적용 제외 | L336–355 |
| failure behavior 표 11행 + "차단은 저수준 driver 재시도 초대가 아님" | L357–375 |
| STOP 조건 교차 — 실제 test profile의 server/database 대응 사실을 모르면 expected-target에 추측으로 채우지 않는다 | L377–388 (특히 L386) |
| implementation acceptance criteria 13개 항목 + "실제 production mutation은 테스트 케이스로 쓰지 않는다, fake/승인 테스트 인프라" | L390–421 |
| Non-goals — SQL parser 미구현, #23 재정의 금지, #19 의미론 결정 금지, #18/#19/#21/#22 도구 구현 금지, 비상 production-write 절차 미정의 등 | L423–436 |

의존 문서 2건도 전문 읽었다: `docs/12-db-connection-secrets-contract.md`(210줄,
#23)와 `docs/issue-19-mssql-test-materialization.md`(210줄, #19 — CLOSED 상태의
design-only 문서). `scripts/db/connection_profiles.py`(117줄)도 현재 구현 그대로
전문 읽었다(게이트 3).

### 게이트 2 — 이슈 본문의 stale recommendation을 그대로 구현하지 않는가 → 통과

이슈 #20 본문 대비 확정된 차이 (merged canonical design이 우선, 계획 원칙 1):

| 이슈 본문 권고 | 현재 설계의 판정 | 구현 시 지침 |
|---|---|---|
| `prod-readonly`, `test-readwrite` 같은 명시적 profile 이름 분리 | profile 어휘는 #23 canonical이 소유 — 정확히 `mssql-prod-ro` / `mssql-test-rw` / `postgres-test-rw` (설계 L105–107). #20은 "생성"이 아니라 "소비"만 한다 (L109) | #23 resolver를 통해서만 profile 해결. 본문의 이름 체계 신설 금지 |
| INSERT/UPDATE/DELETE/EXEC("부작용 있는 SP") 요청이 `test-readwrite`가 아니면 예외·중단 | 방향(코드 강제)은 승계했으나 메커니즘이 불충분 — finding 1(L24): MERGE/TRUNCATE/DDL/`SELECT INTO`/bulk-load 누락, finding 2(L25): 키워드 매칭은 신뢰할 수 없는 인가 메커니즘, finding 3(L26): profile 이름이 test인 것 자체는 증명 아님 | Layer 4 capability API가 권한 경계(L175)이고 분류기는 방어선: 6-class 보수 분류(unknown → 거부, L188) + 이름 아닌 실제 identity attestation(L133–158). 키워드 블랙리스트만으로 인가하는 구현 금지 |
| profile↔대상 매핑을 `config/db_connections.example.json` 등 설정 파일로 관리 + test 호스트명이 운영과 유사하면 경고 | config-file 경로는 #23 finding 1이 병립 비밀 경로로서 거부(설계 L109–110도 "caller-defined profile aliases / raw connection strings" 금지). 유사성 경고는 finding 4(L27)로 부정 — "위험 실행은 positive target-identity match, 모호하면 차단"; L158은 유사성 진단을 선택적 진단으로 강등 | expected-target은 **비밀이 아닌** 안전 메타데이터로 최소 repository 표현(L113–118, L120) — 인-코드 레지스트리(§3 P-3). JSON/설정 파일 신설 금지. 유사성 진단은 v1 미구현("may" — 선택) |
| 모든 위험 동작 실행 전 SQL 구문과 대상 프로필을 stdout에 명시적 로그 | 전체 SQL 기록은 finding 7(L30)이 정확히 금지하는 것 — redacted 표현 + stable hash만(L305–318), parameters/PII/row 값 미기록(L311–316) | 구조화 audit event(T-4): literal 마스킹 normalized preview + sha256 hash. 원문 SQL·파라미터 값 절대 미기록, sentinel 테스트로 강제 |
| (본문 유효 부분) 서버단 read-only 계정을 1차 방어선으로 문서 권고 | 그대로 승계 — Layer 1(L83–97)이 이 권고를 계약화. guard가 쓰기를 시도해 read-only를 검증하는 것 금지(L95) | Layer 1은 provisioning/문서 영역 — 런타임 코드 없음(§3 P-9) |
| (본문 유효 부분) 이 가드를 모든 DB 쓰기 스크립트의 필수 진입점으로 | 승계 — L16(모든 DB 도구가 하나의 guard 소비) + L336–355(우회 방지) | #18/#19/#21/#22 소비는 각 이슈 범위(§3 P-10). #20은 경계 제공까지만 |

본문의 문제 진단(운영 DB 파괴가 최대 blast-radius, 산문이 아닌 코드 강제 필요)은
설계가 그대로 승계했다. stale 본문을 그대로 따르는 항목은 없다.

### 게이트 3 — 선행 contract가 실제 main에 구현되어 있는가 → 통과

D-F 레인상 #20의 선행은 #23뿐이다. 현재 `main`의 실제 파일에서 확인:

| 전제 요소 | 위치(`44949a5`) | 확인 내용 |
|---|---|---|
| #23 resolver | `scripts/db/connection_profiles.py` (117줄) | `resolve_connection_profile(profile_name, *, allowed_profiles=None, operation="read", environ=None)` — operation `"write"` × read-only profile 거부, allowlist 위반 거부, env unset/empty 거부, `ProfileResolutionError` 메시지는 비밀 미운반. `PROFILES`는 `MappingProxyType`으로 runtime-immutable(HANDOFF 재검증: item assignment → `TypeError`). #20이 필요로 하는 소비 표면이 그대로 존재 |
| #23 profile 메타데이터 상수 | 같은 파일 L15–21 | `ENGINE_MSSQL`/`ENGINE_POSTGRESQL`, `ENVIRONMENT_PRODUCTION`/`ENVIRONMENT_TEST`, `CAPABILITY_READ_ONLY`/`CAPABILITY_READ_WRITE`, `OPERATIONS` — Layer 2/3 판정이 임의 문자열 없이 소비 가능 |
| `.env.example` | 3개 canonical key, RHS 전부 빈 값 | #23 계약 L113–117 그대로 — #20은 무변경 소비 |
| validator 배선 선례 | `scripts/validate_scaffold.py:829` `validate_env_example_contract()`, `main()` 체인 `:2729` 배선 | T-5(신규 독립 검사 함수 additive 추가)가 따를 정확한 패턴 — #5/#7/#8/#13/#14/#6/#23 선례 |
| 테스트 기반 | `scripts/tests/` 15개 파일, 434 passed | `test_db_connection_profiles.py`, `test_env_example_contract.py` 선례 — 도메인별 파일 분리 관례(#20도 `test_db_*.py` 신규 파일) |
| driver/dotenv 무결 전제 | `scripts/` 전체 grep `pyodbc\|psycopg\|sqlalchemy\|pymssql\|dotenv` → 무검출(예외 2건은 gitignore 규칙을 다루는 테스트 함수명) | `scripts/db/connectors/` 신설 전 무엇도 driver를 import하지 않음 — T-5 검사의 green 출발 상태 |
| pytest 실행 환경 | `scripts/tests/conftest.py` — repo root sys.path | `scripts.db.*` 네임스페이스 import 관례(#23 P-1과 동일하게 `__init__.py` 불요) |
| CI 형태 | `.github/workflows/ci.yml` `repo-guards` job = validator + OQ + doc-links | acceptance 12("CI or an equivalent deterministic repository check")는 validator additive 함수로 충족 — CI workflow 파일 무변경 |
| #19 상태 | Issue #19 CLOSED(미구현), `docs/issue-19-mssql-test-materialization.md`는 design-only | **#20의 선행이 아님** — #19 설계 L42가 오히려 "Implementation of #19 is blocked until #20 and #23 establish their contracts"라고 명시(의존 방향 #19 → #20). 아래 명시적 확인 참조 |

### 게이트 4 — 사용자의 명시적 구현 승인 → 조건부 통과 (이번 세션은 구현 없음)

- `AGENTS.md` rule 13 (design gate) 유효.
- HANDOFF.md 최신 항목(`44949a5`, 2026-08-24): "Track D continues at #20 … Before
  starting #20, redo the '구현 시작 전 체크' 7-item gate against current `main`
  (same process #23 used)" + "**Rule-13 Track P/D authorization remains in effect
  and has not been revoked.**" — 본 세션 지시가 바로 그 게이트 재실행 + 실행 계획
  작성이다. Track P 전 이슈와 #23에서 동일 standing authorization이 issue-by-issue
  구현의 근거로 연속 적용됐다.
- ISSUES-PLAN-DRAFT 원칙: "이 계획 문서 또는 PR의 merge만으로 승인됐다고 간주하지
  않는다." **본 실행 계획 문서 자체가 구현 승인이 아니다.** 본 세션 지시는
  "게이트 체크 + 실행 계획 문서 + 커밋"으로 한정되어 있으므로 **본 세션에서는
  `scripts/db/db_guard.py` 등 구현 코드를 작성하지 않는다.** 구현 세션(codex)은
  standing authorization과 이 게이트 결과가 green임을 재인용한 뒤 착수한다.
- 게이트 결과에 블로커가 없으므로 별도 승인 질의 항목은 없다. 다만 §3 P-3이
  지적하는 잔여 사실(실제 expected-target 값은 사용자가 공급해야 하는 배포 사실)은
  구현 완료 후 T-H1에서 사용자에게 명시적으로 전달한다.

### 게이트 5 — 구현 범위가 acceptance criteria를 넘지 않는가 → 통과

범위 상한 = 설계 "Implementation acceptance criteria" 13개 항목(L394–419) +
"Failure behavior" 표 전 행(L361–373) + "Bypass prevention in repository
structure"(L336–355). 구체적으로:

- 변경/신규: `scripts/db/target_metadata.py`(신규), `scripts/db/sql_classification.py`
  (신규), `scripts/db/connectors/base.py`·`mssql.py`·`postgresql.py`(신규),
  `scripts/db/db_guard.py`(신규), `scripts/tests/test_db_target_metadata.py`·
  `test_db_sql_classification.py`·`test_db_connectors.py`·`test_db_guard.py`(신규),
  `scripts/validate_scaffold.py`(신규 독립 검사 함수 2건 + 상수 + `main()` 배선
  2줄 — 경계 검사·target-metadata 모양 검사),
  `scripts/tests/test_db_driver_boundary.py`(신규), `HANDOFF.md`(T-H1).
- 비변경(Non-goals L423–436 + 게이트 2): `docs/12-db-execution-safety-contract.md`·
  `docs/12-db-connection-secrets-contract.md`·`scripts/db/connection_profiles.py`·
  `.env.example`·`.gitignore`(전부 #23/설계 소유 — 읽기 전용 소비), #18/#19/#21/#22
  도구·문서, SQL parser 및 parser 의존성(L427 — 표준 라이브러리 tokenizer만),
  4번째 profile·production-RW profile·두 번째 비밀/설정 경로, `--force`/`--unsafe`/
  확인 프롬프트/attestation 무효화 env/unknown 강등 플래그/raw connection 노출
  (L322–334), 실제 DB 연결·승인 인프라 없는 통합 검증(L421 — 테스트는 fake 전용),
  dependency manifest 신설·hard driver 의존성(§3 P-7 — lazy import만), CI workflow
  파일 변경, `docs/05-open-questions.md` 상태 변경(OQ-014·OQ-021 무관 유지),
  FastAPI `target/backend` persistence 층(L355 자동 적용 제외).

### 게이트 6 — 새 lock-in 결정 시 design gate 재오픈 근거 → 통과

재오픈 메커니즘이 3중으로 존재: ISSUES-PLAN-DRAFT 계획 원칙 2("설계 재개방 금지.
구현 중 새로운 lock-in 결정이 필요해지면 임의 결정하지 않고 해당 design gate를
다시 연다"), AGENTS.md rule 13, 본 계획 §5의 명시적 트리거 11개. #20은 Track D
최고 lock-in 위험 항목이므로(HANDOFF: "highest-lock-in-risk item in Track D")
트리거를 구현·리뷰 세션에 그대로 전달한다.

### 게이트 7 — shared file merge 순서 → 통과

- `gh pr list` open PR 없음(본 세션 확인). 본 브랜치 = `origin/main`(`44949a5`)
  분기 직후, 커밋 없음(`git diff origin/main HEAD` 빈 출력).
- 로컬 잔존 브랜치 `hjung3113/issue9-followup`·`hjung3113/issue13-stop-condition`·
  `hjung3113/issue23-plan`: 전부 squash-merge 이전 stale 사본(내용은 이미 `main`에
  반영). #20 파일과 교집합 없음. 작업 대상 아님.
- `scripts/validate_scaffold.py` 충돌 패턴: T-5는 기존 함수 내부 확장이 아니라
  **신규 독립 함수 additive 추가**(#5/#7/#8/#13/#14/#6/#23 선례) — `main()`의
  errors 통합 지점 1줄만 공유. 해당 파일을 수정하는 진행 중 작업 없음(위 확인).
- `scripts/db/` 소유권: 현재 유일 파일 `connection_profiles.py`는 무변경.
  신규 파일 5개 + 테스트 5개는 전부 #20 소유. Track D 후속(#18, #22 core)은
  #20 merge 이후 착수(Track D merge 순서 2→3) — `db_guard` 소비 경합 없음.
- 리뷰 예산: HANDOFF 명시 — "**For #20 … budget for at least two independent
  review passes before treating it as mergeable, not one**"(검증-스케일링 원칙 +
  PR #66/#67/#68에서 3회 연속된 "checks the shape, not the substance" 신규
  validator 초회 결함 계열). DAG에 독립 리뷰 2회(T-R1, T-R2) + 소유자 수준 패스를
  명시적으로 예산화한다(§4). 이는 #23의 1회(T-R1)+소유터치 패턴을 상회하는 #20
  전용 강화다.

### 명시적 확인 — #20 구현의 #19 materialization 의존 여부 (ISSUES-PLAN-DRAFT L102)

상위 계획 L102와 본 세션 지시가 요구한 확인. 판정: **#20의 구현은
`docs/issue-19-mssql-test-materialization.md`의 materialization 개념
(manifest, allowlist, masking/sanitization, source-consistency, fresh-target 등)에
의존하지 않는다.** 근거:

1. 의존 방향이 반대다 — #19 설계 L42: "Implementation of #19 is blocked until #20
   and #23 establish their contracts. The materializer must consume those
   contracts." #19가 #20을 소비한다.
2. #20 설계 L54는 #19를 materialization 의미론의 authoritative source로 지정할
   뿐이고, L275는 "The guard does not own #19's manifest, masking/classification,
   fresh-target, source-consistency, or evidence rules"라고 명시 소유권을 배제한다.
3. #20 설계 L244–249는 test read-write의 예시 소비 workflow로 #19를 "예시로" 열거할
   뿐("such as"), guard가 workflow를 검증하지 않는다 — capability 발급이 전부다.
4. #20 acceptance criteria 13개 항목(L394–419)과 failure 표(L361–373) 어디에도
   materialization 개념이 없다. "source/target identity collision" 항목도
   guard 수준(L129 test identity == production identity 거부, Layer 3 mismatch
   차단)에서 #19 개념 없이 정의된다.
5. Non-goals L429가 "decide #19 masking/subsetting/materialization semantics"를
   명시적으로 금지한다.
6. 유일한 미약한 접점은 설계 L320("#19 may persist higher-level materialization
   evidence ...; that evidence references guard/run metadata")이다 — 이는 본
   계획의 audit 이벤트 필드(P-6, L295–309)로 이미 충족 가능하며, #20이 별도의
   run-id 핸들 API를 제공해야 한다는 요구가 아니다(본 세션 재확인: L320는
   #19 증거가 guard audit을 "참조"한다는 redaction 규칙이지 guard 공개 API
   의무를 부과하지 않는다). 이후 #19 구현이 더 풍부한 run 핸들을 요구하면
   그때만 §5 트리거 1/8 경로의 신규 API 결정이다 — 본 판정(의존 없음)은
   유지된다.

따라서 본 계획은 #19 재오픈을 제안하지 않고, #20을 설계 범위 그대로(attestation +
capability 경계, 소비 도구 부재)로 계획한다. **구현 중 이 판정이 깨지는 순간
(예: guard가 TestWriteSession 발급 전 "#19 manifest 승인" 같은 개념을 요구하게
되는 경우) §5 트리거 1에 따라 중단하고 사용자에게 #19 재오픈 여부를 질의한다 —
임의 재구현·임의 축소 금지.**

---

## 2. 현재 구현 기준선 (구현 세션이 기대해야 하는 출발 상태)

### `scripts/db/` (유일 파일: `connection_profiles.py`)

#23 구현체. #20이 소비하는 정확한 표면:

```python
ENGINE_MSSQL = "mssql"; ENGINE_POSTGRESQL = "postgresql"
ENVIRONMENT_PRODUCTION = "production"; ENVIRONMENT_TEST = "test"
CAPABILITY_READ_ONLY = "read-only"; CAPABILITY_READ_WRITE = "read-write"
OPERATIONS = ("read", "write")

@dataclass(frozen=True)
class ConnectionProfile: name, env_var, engine, environment, capability

PROFILES: Mapping[str, ConnectionProfile]   # MappingProxyType — runtime-immutable, key 3개 고정

class ProfileResolutionError(Exception): ...          # 비밀 미운반
@dataclass(frozen=True)
class ResolvedProfile: profile, connection_value      # connection_value: repr=False

def resolve_connection_profile(profile_name, *, allowed_profiles=None,
                               operation="read", environ=None) -> ResolvedProfile
```

거부 조건(전부 연결 시도 전): unknown profile / allowlist 위반 / invalid
operation / write × read-only / env unset / env empty·whitespace. 이 파일은
**무변경**(게이트 5) — #20은 import해서만 소비한다.

### `scripts/` 구조와 validator

`scripts/db/` 외: validator 4개 + `tests/`. `scripts/__init__.py`·`scripts/db/
__init__.py` 모두 없음 — conftest가 repo root를 sys.path에 넣어 네임스페이스
패키지로 import. `scripts/db/connectors/`도 `__init__.py` 없이 동일 관례(§3 P-1).
`scripts/validate_scaffold.py` 2,742줄 — `validate_env_example_contract()`:829,
`collect_validation_errors()`:2706, `main()`:2720(배선 :2729). 진단 형식 관례
`path:line [category] message`. T-5의 신규 함수·상수는 이 관례를 따른다.

### 테스트·CI 기반

`scripts/tests/` 15개 파일 434 passed(본 세션 실측). CI `repo-guards` job =
`validate_scaffold.py` + OQ + doc-links — pytest는 로컬/리뷰 회귀용(#23과 동일).
T-5가 validator에 배선되면 CI가 자동으로 driver 경계를 강제한다(acceptance 12).

### 배포 사실 공백 (설계가 예견한 정상 상태)

현재 저장소는 어느 profile이 실제 어떤 server/database를 가리키는지 알지 못한다
(OQ-014 관련 인프라도 부재). 설계 L386은 이 경우 expected-target 메타데이터에
**추측을 채우지 말 것**을 명시한다. 따라서 §3 P-3대로 레지스트리는 미해결(빈 값)로
출하하고 모든 실제 세션은 fail-closed 차단된다. 이것은 결함이 아니라 계약이
요구하는 정직한 상태다. 값 공급은 사용자의 별도 입력 사항이다(T-H1에서 전달).

---

## 3. 파생 판정 사항 (신규 lock-in 아님 — 근거 명시)

구현 중 아래 판정은 임의 결정이 아니라 병합된 `docs/12`에서 유도된다.
구현자/리뷰어가 유도 근거에 동의하지 않으면 그때만 design gate를 재오픈한다.

- **P-1. 모듈 경계 = `db_guard.py`(유일 공개 경계) + `connectors/{base,mssql,
  postgresql}.py` + `sql_classification.py` + `target_metadata.py`, `__init__.py`
  없음.** 근거: 설계 L343–349의 구조 스케치가 `db_guard.py`("profile/safety/
  capability boundary")와 `connectors/`("engine-specific driver + identity
  probes")를 지정 — "such as" 예시이므로 같은 경계 안의 파일 분할은 구현 자유
  (#23 P-1 선례). 분류기와 메타데이터를 별도 모듈로 분리한 것은 파일 단일
  책임 + 리뷰 분리 때문이고, `connectors/base.py`는 driver import 없는 공유
  타입(`AttestedIdentity`, 프로토콜)만 담아 순환 import를 막는 최소 조치다.
  네임스페이스 패키지 관례는 #23 P-1과 동일.
- **P-2. 공개 API = `open_readonly(profile_name, *, tool_id, allowed_profiles=None,
  environ=None, connector_overrides=None, metadata=None, audit_sink=None) ->
  ReadOnlySession` / `open_test_readwrite(같은 시그니처) -> TestWriteSession`.
  `ReadOnlySession`은 `fetch_one`/`fetch_all`/`close`(context manager)만,
  `TestWriteSession`은 여기에 `execute`(단일 guarded 경로)만 노출. CLI 없음.**
  근거: L166–169(두 capability 팩토리), L171(RO는 raw execute 경로 금지), L173
  (test 쓰기는 분류·audit 후 위임하는 "one guarded path"), L369(RO의 위험 요청은
  driver 실행 전 차단). keyword-only 주입 인자들은 I/O를 대체할 뿐 검사를 건너
  뛰지 못한다(fake connector가 틀린 identity를 반환하면 attestation이 차단 —
  테스트가 바로 그것을 증명). `tool_id` 필수는 audit 필드 L296의 발급원.
  `allowed_profiles`는 #23 resolver의 동명 파라미터 pass-through(L123 tool
  allowlist). CLI 부재는 #23 P-7과 동일한 YAGNI(현재 소비 도구 없음).
- **P-3. expected-target 메타데이터 = 비밀 아닌 인-코드 고정 레지스트리
  `scripts/db/target_metadata.py`, 초깃값은 전 profile 미해결(빈 문자열) — 실제
  값은 사용자가 공급하는 배포 사실이며 agent가 발명하지 않는다.** 근거: L120이
  "minimal repository/config representation"을 허용하고 두 번째 비밀 경로만 금지
  — identity는 credential이 아니므로 인-코드 `MappingProxyType` 레지스트리
  (#23 `PROFILES` 선례)가 최소 표현이다. 빈 값 출하는 L386("unresolved and must
  not be guessed")의 직접 구현: 미해결 → `get_expected_target`이
  `TargetMetadataError` → 세션 fail-closed. 레지스트리 모양 검증(key가 `PROFILES`
  와 정확 일치, production/test identity 쌍 충돌 부재, 중복 쌍 부재)은 테스트가
  강제하고(L122–129의 기계화), **빈 값 자체는 모양 결함이 아니라 합법적 전이
  상태**로 취급한다(값은 런타임 차단으로 처리). 설정 파일·env var 형태는 금지
  (게이트 2, 두 번째 경로).
- **P-4. attestation 비교 = (engine, server_identity, database_identity) 3중 정확
  일치(양쪽 `strip()` 후 대소문자 그대로), probe의 어떤 예외·timeout도 차단.
  유사성 진단은 v1 미구현.** 근거: L144–152가 exact equality를 요구하고 L154가
  mismatch·missing·probe 실패·timeout·모호 결과 전부를 차단. 대소문자 무시 정규화
  도입하지 않는다 — 서버 의미론보다 엄격한 쪽은 오차단(fail-closed 방향)일 뿐
  오승인을 만들지 않고, 값은 사용자 승인 상수라 맞추면 된다. L158의 유사성 진단은
  "may emit" 선택 사항이므로 YAGNI로 제외(필요 시 별도 추가).
- **P-5. 분류기 = 표준 라이브러리 보수 tokenizer 기반 6-class 분류, read는 명시
  allowlist로만 인정, 그 외 전부 `unknown` → 거부. batch는 최대 위험 계승,
  `unknown` 포함 batch는 결코 `read`로 강등되지 않음. transaction 제어(`BEGIN`/
  `COMMIT`/`ROLLBACK`)/`SET`/`USE`/`DECLARE`/`GO`는 v1에서 `unknown`.** 근거:
  L427(Non-goal: SQL parser 미구현) + L25/finding 2(키워드 매칭은 신뢰할 수 없는
  **인가** 메커니즘) — 그래서 분류기는 인가가 아니라 Layer 4 capability API의
  방어선(L175)이고, 알 수 없는 것은 전부 거부(L188)하는 방향으로만 보수적으로
  설계한다. tokenizer는 주석(`--`, 중첩 `/* */`)·문자열(`N'...'`, `''` escape)·
  식별자 quote(`[ ]`, `" "`)/깊이 0 세미콜론 batch 분할을 인식해 L195(주석·공백·
  대소문자·순서가 인가를 바꾸지 못함)와 finding 1·2의 우회(문자열 내 키워드,
  주석 은닉, `SELECT ... INTO`, `MERGE`/`TRUNCATE`, `EXEC` 생략형 bare 프로시저
   호출)를 막는다. read allowlist는 `INTO` 없는 `SELECT`와 최종 문이 `SELECT`인
   `WITH` CTE뿔인데, **`INTO`·위험 동사 토큰은 "최상위 깊이"가 아니라 문장 내
   어느 깊이에서든 부재해야 한다**(T-2 상세 — CTE 본문 `SELECT ... INTO`,
   PG data-modifying CTE, 구분자 없는 다중 문장 3종 우회의 구조적 봉쇄).
   rollback 포장 강등 금지(L197)는 문장별 분류 + batch 최대 위험
   계승으로 자연 성립. **설계 failure 표 9행의 조건 열에 `unknown`이 포함돼
   "test 쓰기 세션에서는 unknown 포함 batch도 허용"으로 읽을 여지가 있으나**
   L188(`unknown` → denied, 대상 무제한정)·L194(unknown 포함 batch는 denied)·
   L372(판단 불능 → block)를 함께 읽으면 보수적 판독은 **unknown 포함 batch는
   test 쓰기 세션에서도 거부**다 — `BATCH_RANK`의 `unknown`(3) >
   mutation/ddl/procedure-exec(2)이 그 구현이며, 모호성의 fail-closed 해석일
   뿐 임의 완화가 아니다(완화는 아래 트리거 5 경로만). transaction 제어 등을
   `unknown`에 두는 것은 어떤 현 소비
   도구도 그것을 필요로 하지 않기 때문이고(현재 소비 도구 0), 필요해지면 §5
   트리거 5(허용 목록 확장 = 정책 변경)이다. parser 의존성 추가는 금지(트리거 4).
- **P-6. audit = 호출자 sink(기본 stderr)로의 단일 줄 JSON 이벤트, 필드는 L295–309
  최소 집합 그대로, preview/hash는 분류기의 literal 마스킹 정규형에서 파생,
  위험 연산 pre-audit sink 실패 시 실행 차단. `open_test_readwrite` 세션 개방
  실패(예: attestation mismatch)도 `operation_class: null`로 audit 발행.** 근거:
  L291(stdout/stderr 또는 명시 sink), L295–309(필드), L305–318(preview는
  redacted, hash는 stable — 원문 SQL·파라미터·row 값 미기록 L311–316, finding 7),
  L373(pre-audit 불능 → 위험 실행 차단). preview = 정규형 앞 200자, hash =
  정규형 전문의 sha256 hexdigest(literal이 `?`로 마스킹되므로 값이 달라도 구조가
  같으면 동일 hash — 상관관계용). 세션 개방 실패 audit은 "hazardous attempts are
  auditable"(L15)의 가장 안전 쪽 해석이다(운영 identity로 지목된 test 쓰기 시도가
  흔적 없이 지나가는 것을 방지). read-only 세션 개방은 위험 시도가 아니므로 미발행.
- **P-7. connectors = lazy driver import(`pyodbc`/`psycopg`) — hard 의존성·
  dependency manifest 신설 없음, driver 부재 시 `ConnectorError` → guard 차단.
  identity probe는 서버 측 읽기 전용 질의 + driver 연결 속성.** 근거: L343–349가
  engine별 driver+probe를 요구하지만 저장소에 dependency manifest가 없고
  (PR #58 P2 선례 — 외부 의존성 추가는 clean checkout을 깨뜨림), 테스트는 fake
  전용(L421)이므로 driver는 connector 내부 함수에서 처음 사용될 때 import한다
  (실행 환경에 driver가 없어도 모든 guard 로직·테스트가 동작). probe: MSSQL은
  `SELECT @@SERVERNAME` / `SELECT DB_NAME()`, PostgreSQL은 `SELECT
  current_database()` + 연결 객체의 host/port 속성(연결 문자열 직접 parsing 없음
  — #23의 "opaque connection value" 존중). engine 성분은 connector 상수가
  제공하고 guard가 `profile.engine`과 비교(L150). probe SQL 자체가 `read` class로
  분류되는지 테스트로 고정(procedure drift 방지).
- **P-8. 우회 방지 정적 검사 = `validate_scaffold.py`에 신규 독립 함수
   `validate_db_driver_boundary()` additive 추가(AST import 스캔 + 동적 import
   통로 금지). 금지 대상 = 외부 MSSQL/PG 도달 가능 driver 8종(`pyodbc`,
   `pymssql`, `psycopg`, `psycopg2`, `sqlalchemy`, `asyncpg`, `pg8000`,
   `adodbapi`) — 마지막 3종은 비동기 PG·pure-Python PG·Windows ADO 경로로,
   열거에서 빠지면 B1 자체가 우회로가 된다(finding 9는 "직접 driver import"
   일반이지 특정 5종이 아니며, 현재 저장소 사용 0 — 본 세션 grep 확인) — 의
   import와 `scripts.db.connectors` import(+ 상대 import 형태)를, `scripts/**`
   전체(단 `scripts/db/
   connectors/**` 제외)에서 차단. 허용 예외는 열거 상수만.** 근거: L351("CI/static
  validation should reject direct DB-driver imports … outside the approved
  connector/guard boundary … AST/import checks or an equivalent deterministic
  rule; must not rely only on code-review convention") + acceptance 12 + #23 T-2
  배선 선례(CI `repo-guards`가 자동 강제). `connectors` 직접 import 차단은
  finding 9(L33: "callers can still import DB drivers directly and obtain raw
  writable connections")의 guard-우회 경로 차단 — 허용 importer는 `db_guard.py`,
  `connectors/` 내부, 열거된 connector 테스트 파일뿉. `sqlite3`은 범위 밖
  (MSSQL/PG에 도달할 수 없어 위협 모델 밖 — 과잉 금지는 YAGNI 위반). 예외는
  파일명·의도 추론이 아니라 명시 튜플로만(L353). FastAPI `target/backend`는
  검사 범위에서 제외(L355).
- **P-9. acceptance 항목 2(서버단 read-only 계정)는 런타임 코드가 아니다.** 근거:
  L95가 "The guard must never verify read-only status by attempting a write"를
  명시 — 즉 이 요구의 코드 부분은 존재하지 않는다(검증 금지). provisioning/증거는
  운영 사항이고(L87–93), guard의 책임은 계정이 과권한이어도 독립적으로 위험 실행을
  거부하는 것(L95–97, L240) — 그것은 T-4의 RO 차단으로 이미 구현된다. 별도 문서
  신규 작성은 하지 않는다 — AC2의 "documented"는 docs/12 자체(L83–97)가 담당하고,
  `.env.example` 현행 주석은 profile 용도·capability만 기술한다(server-enforced
  read-only 요구는 기술하지 않음 — 본 세션 확인. #23 소유 파일이라 본 계획이
  고치지도 않는다). 따라서 "계정이 실제 read-only로 provision됐다"는 배포 사실은
  expected-target 값과 함께 T-H1에서 사용자에게 명시적으로 전달하고 확인을
  받는다(AC2를 완료로 보고하는 조건에 사용자 확인 포함).
- **P-10. acceptance 항목 11(#18/#19/#21/#22가 공통 경계 소비)은 "제공" 기준.**
  근거: 소비 도구가 아직 존재하지 않고 L430 Non-goal이 그 구현을 명시 금지 — #23
  실행계획의 동일 패턴(acceptance "#18–#22 사용" 행을 "이후-소비 기준"으로 표기)
  그대로. #20은 소비 가능한 공개 API(P-1/P-2) + 경계 강제(P-8)를 제공하고, 각
  도구의 실제 배선은 각 이슈 범위에서 완료 판정한다.
- **P-11. #19 의존 없음 판정(§1 명시적 확인)을 계약 조건으로 유지.** 근거: 상위
  계획 L102 + 설계 L54/L244–249/L275/L429. 구현·리뷰 중 materialization 개념
  필요성이 발견되면 §5 트리거 1로 즉시 중단하고 사용자 판단(#19 재오픈 또는 #20
  범위 축소)을 기다린다 — 어떤 방향도 세션 내 임의 결정 금지.
- **P-12. 테스트는 전부 fake 기반이며 acceptance 13개 + failure 표 11행에 1:1 대응
  테스트가 존재해야 한다.** 근거: L421("Actual production mutation is never used
  as a test case … fakes or approved test infrastructure to prove the production
  branch blocks before the driver sees the hazardous operation") + L407–419 목록.
  fake connector/driver는 호출 기록을 남겨 "차단이 driver 실행 전인지"를 증명하고,
  sentinel 값(env value·파라미터·row에 심은 `SECRET-VALUE`)의 audit/오류 부재를
  전 경로에서 단언한다(#23 T-1 테스트 8 패턴).

---

## 4. 태스크 분해 (DAG)

원칙: 병렬 그룹 A(T-1 메타데이터 ∥ T-2 분류기 ∥ T-3 커넥터 ∥ T-5 정적 검사)는
파일이 완전 분리되어 병렬 가능하다. T-4(guard 본체)는 T-1/T-2/T-3의 공개
인터페이스를 소비한다. 물리적으로는 **단일 브랜치/단일 PR**로 출하한다(§7).

```text
T-0 (완료: 이 문서) 게이트 체크 + 실행 계획
     |
     v
[병렬 그룹 A]  T-1(target_metadata) ∥ T-2(sql_classification) ∥ T-3(connectors) ∥ T-5(validator 경계 검사)
     |   (T-3의 "probe SQL이 read로 분류됨" 테스트만 T-2 인터페이스에 의존 — 그룹 내 순서 무관, 세션 내 순차 처리)
     v
T-4 db_guard.py — 세션·attestation·audit (T-1/T-2/T-3 인터페이스 소비)
     |
     v
T-I1 통합 검증 (validator + 전수 pytest + doc links/OQ + 비범위 무변경 + 무단 import 부재)
     |
     v
T-R1 독립 adversarial review — 1차 (fresh subagent, 2단계: PR 본문 → diff/repo; AGENTS.md rule 10)
     |     → 발견 수정 + re-verify
     v
T-R2 독립 adversarial review — 2차 (두 번째 fresh subagent — HANDOFF 명시: #20은 리뷰 2회 이상 예산)
     |     → 발견 수정 + re-verify + 소유자 수준 패스 (PR #66/#67/#68 "checks the shape, not the substance" 계열 예방)
     v
T-H1 HANDOFF.md 갱신 + Issue #20 구현 코멘트 + PR 개설(merge는 사용자 명시 지시 대기)
```

### 태스크 목록

| ID | 설명 | 대상 파일 | 선행 | 병렬 그룹 |
|---|---|---|---|---|
| T-0 | 게이트 7항목 재확인 + #19 의존 판정 + 본 실행 계획 작성·커밋 | `migration/ISSUE-20-EXECUTION-PLAN.md` | — | — (본 세션, 완료) |
| T-1 | expected-target 레지스트리 + 모양 검증 + 테스트 | `scripts/db/target_metadata.py`(신규), `scripts/tests/test_db_target_metadata.py`(신규) | T-0 | A |
| T-2 | 6-class SQL 분류기(redaction/정규형 포함) + 테스트 | `scripts/db/sql_classification.py`(신규), `scripts/tests/test_db_sql_classification.py`(신규) | T-0 | A |
| T-3 | engine 커넥터(lazy driver + identity probes) + 테스트 | `scripts/db/connectors/base.py`·`mssql.py`·`postgresql.py`(신규), `scripts/tests/test_db_connectors.py`(신규) | T-0 (테스트 일부 T-2 의존) | A |
| T-4 | guard 본체: 세션·attestation·capability 강제·audit + 테스트 매트릭스 | `scripts/db/db_guard.py`(신규), `scripts/tests/test_db_guard.py`(신규) | T-1, T-2, T-3 | — |
| T-5 | driver/connector import 경계 정적 검사 + 테스트 | `scripts/validate_scaffold.py`(신규 독립 함수), `scripts/tests/test_db_driver_boundary.py`(신규) | T-0 | A |
| T-I1 | 통합 검증 | (수정 대상 없음 — 검증 단계) | T-1..T-5 | — |
| T-R1 | 독립 adversarial review 1차 | (리뷰 보고) | T-I1 | — |
| T-R2 | 독립 adversarial review 2차 + 소유자 수준 패스 | (리뷰 보고) | T-R1 | — |
| T-H1 | HANDOFF 갱신 + Issue 코멘트 + PR 개설 | `HANDOFF.md`, GitHub | T-R2 | — |

### T-1 — `target_metadata.py`: expected-target 레지스트리

**대상 파일**: `scripts/db/target_metadata.py`(신규),
`scripts/tests/test_db_target_metadata.py`(신규). 선행: T-0.

공개 인터페이스(P-3):

```python
"""Non-secret expected-target identity registry for the DB execution
safety guard. Contract: docs/12-db-execution-safety-contract.md
(Issue #20) Layer 2 (L111-131). These are SAFETY METADATA, not
credentials: no connection values here, ever (docs/12 L120).
Identity values are deployment facts owned by the user; until real
approved identities are supplied they stay UNRESOLVED (empty) and the
guard fails closed (docs/12 L386: never guess into this registry).
"""
from types import MappingProxyType

@dataclass(frozen=True)
class ExpectedTarget:
    server_identity: str     # "" = unresolved
    database_identity: str   # "" = unresolved

EXPECTED_TARGETS: Mapping[str, ExpectedTarget] = MappingProxyType({
    "mssql-prod-ro":    ExpectedTarget("", ""),
    "mssql-test-rw":    ExpectedTarget("", ""),
    "postgres-test-rw": ExpectedTarget("", ""),
})

class TargetMetadataError(Exception): ...  # 메시지는 profile 이름·필드명만

def get_expected_target(profile_name: str, *, targets=EXPECTED_TARGETS) -> ExpectedTarget
    # key 부재 / server_identity=="" / database_identity=="" → TargetMetadataError
    # (설계 L127 "expected target identity is missing or ambiguous" → block)

def validate_target_metadata(*, profiles=PROFILES, targets=EXPECTED_TARGETS) -> list[str]
    # 모양 결함만 보고(빈 값은 전이 상태로 보고하지 않음 — P-3):
    # M1 targets key 집합 != profiles key 집합 (양방향 drift)
    # M2 production profile의 (server, database) 쌍과 test profile의 쌍이 동일
    #    (설계 L129 "a test target identity equals an approved production identity")
    # M3 서로 다른 두 profile의 쌍이 동일(=모호) — engine이 다르면 제외(쌍은
    #    engine 성분 없이 비교하되 engine 불일치 쌍은 위협이 아님)
    # M4 server/database identity에 앞뒤 공백 존재(정확 일치 비교 무결화)
```

구현 요구:

- `PROFILES`는 `from scripts.db.connection_profiles import PROFILES, ConnectionProfile`
  import로 소비(상수 재정의 금지 — 드리프트 방지).
- 레지스트리 값 변경(실제 identity 공급)은 사용자 제공 배포 사실의 반영 시에만
  이뤄지며, 그 시점에도 이 모듈의 코드(검증 규칙)는 변하지 않는다.
- 오류 메시지는 profile 이름·필드명만 포함(연결 값 취급 자체가 없음).

테스트(`test_db_target_metadata.py`):

1. `EXPECTED_TARGETS` key 집합 == `PROFILES` key 집합(양쪽 import, 정확 일치).
2. `get_expected_target`: 미해결(빈) server/database → 각각 `TargetMetadataError`;
   값 있으면 반환; 알 수 없는 profile 이름 → 오류.
3. `validate_target_metadata` M1: 합성 targets에서 key 누락·추가 각각 보고.
4. M2: 합성 targets에서 `mssql-test-rw` 쌍을 `mssql-prod-ro` 쌍과 동일하게 →
   보고(acceptance 13 "test profile misconfigured to a production identity"의
   레지스트리 측면 + "source/target identity collision"의 정적 측면).
5. M3: 두 test profile 쌍 동일 → 보고.
6. M4: `" prod-srv "` 같은 선행/후행 공백 → 보고.
7. 현재 출하 상태(전 미해결)는 M1–M4 어떤 것도 보고하지 않음(빈 값은 결함 아님).
8. 오류 메시지에 sentinel(`SECRET-VALUE`) 부재 — env sentinel을 심고 전 오류
   경로 단언(레지스트리에는 애초에 비밀이 없다는 구조적 보장의 회귀 방지).

### T-2 — `sql_classification.py`: Layer 5 분류기 + 정규형

**대상 파일**: `scripts/db/sql_classification.py`(신규),
`scripts/tests/test_db_sql_classification.py`(신규). 선행: T-0. 표준 라이브러리만
(`re` 없이도 가능하나 허용 — 외부 의존성은 전부 금지).

공개 인터페이스(P-5/P-6):

```python
OPERATION_CLASSES = ("read", "mutation", "ddl", "procedure-exec", "privileged", "unknown")
BATCH_RANK = {"read": 0, "mutation": 2, "ddl": 2, "procedure-exec": 2,
              "unknown": 3, "privileged": 4}

@dataclass(frozen=True)
class StatementClassification:
    operation_class: str
    normalized_sql: str    # 주석 제거·literal→'?'·공백 정규화 (audit/hash 기준)

@dataclass(frozen=True)
class BatchClassification:
    operation_class: str   # 구성 문장 최대 rank (동률 mutation<ddl<procedure-exec 순)
    statement_hash: str    # 정규화 batch 전문 sha256 hexdigest
    preview: str           # 정규형 앞 200자 (redacted preview)

def classify_statement(sql: str) -> StatementClassification
def classify_batch(sql: str) -> BatchClassification
def redact(sql: str) -> str   # normalized_sql 산출 규칙의 단독 노출 (테스트/audit용)
```

분류 규칙(설계 L181–198 표와 규칙의 기계화 — P-5):

- **tokenizer**: `--` 행 주석, 중첩 `/* */` 블록 주석, `N'...'`/`'...'` 문자열
  (`''` escape), `[...]`/`"..."` 식별자 quote, 숫자/16진 literal, batch 분할 =
  깊이 0 `;` **및** 깊이 0 독립 `GO` 토큰(T-SQL batch 구분자 — 둘 다 문자열·
  주석·괄호 내부에서는 분할 아님). 대소문자 무시 키워드
  인식은 항상 quote 밖 토큰에서만, 토큰 단위 정확 일치로(`[delete]` quote
  식별자·`fn_delete_rows` 같은 단일 식별자는 키워드와 접두 불일치).
- **read 인정(allowlist)**: (a) `SELECT` 시작 문장으로서 문장 전체(**괄호 내부
  포함 전 깊이**)에 `INTO` 토큰과 위험 동사 토큰(아래 verb 매핑의 mutation/
  ddl/procedure-exec/privileged 집합)이 하나도 없을 것; (b) `WITH` CTE 정의
  (괄호 깊이 추적) 이후 최종 문이 `SELECT`이면서 CTE 본문 포함 문장 전체에
  같은 금지 토큰이 없을 것. "최상위 깊이만 검사"로는 CTE 본문 `SELECT ... INTO`
  와 PG data-modifying CTE(`WITH d AS (DELETE FROM t RETURNING *) SELECT *
  FROM d` — 최종 문이 SELECT여도 행을 삭제한다)가 `read`로 오인정된다.
  이 2형태 외에는 어떤 것도 `read`가 아니다.
- **verb 매핑(첫 토큰 기준, 전부 대소문자 무시)**:
  `mutation`: `INSERT`, `UPDATE`, `DELETE`, `MERGE`, `BULK INSERT`, `COPY`,
  `SELECT ... INTO`(위 반례); `ddl`: `CREATE`, `ALTER`, `DROP`, `TRUNCATE`,
  `RENAME`, `COMMENT ON`; `procedure-exec`: `EXEC`, `EXECUTE`, `CALL`,
  `EXEC ... (@var)` 포함 전 형태, `sp_executesql`, bare 식별자 시작 문장(예:
  `dbo.MyProc @p=1` — T-SQL은 EXEC 생략을 허용하므로 식별자 시작은 전부 이 class);
  `privileged`: `GRANT`, `REVOKE`, `DENY`, `BACKUP`, `RESTORE`, `SHUTDOWN`,
  `KILL`, `RECONFIGURE`, `ALTER SERVER`/server·role·login·user 대상 CREATE/ALTER/DROP
  (세부는 verb+다음 토큰 조합의 명시 목록으로);
  `unknown`: 그 외 전부 — `SET`, `BEGIN`/`COMMIT`/`ROLLBACK`, `USE`, `DECLARE`,
  `PRINT`, `WAITFOR`, `GO`, 파싱 불능·빈 문장(빈 문장은 batch에서 제거).
- **전 깊이 위험 토큰 하한(추가 방어)**: 문장의 class는 (첫 토큰 또는 CTE 최종
  문 verb 매핑 결과)와 (문장 내 **어느 깊이에서든** 등장하는 위험 동사 토큰의
  class)의 최댓값으로 확정한다. 첫 토큰만 보면 `;`/`GO` 없이 붙어 들어온 다중
  문장(`SELECT 1 TRUNCATE TABLE t`)이 `read`로 오인정될 수 있고, 그런 blob이
  실제로 서버에서 다중 문장으로 실행되는지는 서버 파서 구현에 달린 문제다 —
  guard는 서버 파서의 문장 분리 행동에 의존하지 않는다(L175: SQL 검사는
  방어선). 이 규칙의 오차 방향은 과차단뿐이다(합법 read에 위험 동사 토큰이
  깊이 무관하게 섞여 있는 경우는 quote 식별자 규칙상 사실상 없다).
- **batch 규칙**: 구성 문장 class의 `BATCH_RANK` 최대값 계승; `unknown`(rank 3)
  포함 시 batch도 `unknown`(read로 강등 금지, L194); `privileged`(4)가 최우선.
  rollback 포장(`BEGIN TRAN; INSERT...; ROLLBACK`)은 INSERT 문장이 `mutation`이므로
  batch도 `mutation`(L197 — 강등 없음).
- **정규형**: 주석 제거·문자열/숫자 literal을 `?`로 치환·연속 공백 축약·문장 간
  `; ` 구분. 이 형태가 preview(200자)와 hash(sha256)의 유일한 원천 — 원문 SQL은
  어떤 경로로도 밖으로 나가지 않는다(P-6, finding 7).

테스트(`test_db_sql_classification.py`) — 최소 목록:

1. class별 대표 문장 전부(read `SELECT`/`WITH..SELECT`, mutation 6종+`SELECT INTO`,
   ddl 6종, procedure-exec `EXEC`/`CALL`/bare/`sp_executesql`, privileged 8종+,
   unknown `SET`/`BEGIN`/`USE`/`DECLARE`/`GO`/빈).
2. **우회 방지**: 문자열 literal 내 `INSERT` 텍스트가 read를 바꾸지 않음; 주석
   은닉(`/* INSERT */ SELECT 1` → read, `-- DROP` 행 주석); 중첩 블록 주석;
   대소문자 혼합(`iNsErT`); 문자열 내 `;` 미분할(`SELECT ';'` 단일 문장);
   `SELECT ... INTO` 변형(공백/줄바꿈 삽입) 전부 mutation; **CTE 본문
   `SELECT ... INTO`**(`WITH x AS (SELECT * INTO t2 FROM src) SELECT * FROM x`
   → mutation); **PG data-modifying CTE**(`WITH d AS (DELETE FROM t RETURNING *)
   SELECT * FROM d` → mutation); **구분자 없는 다중 문장**(`SELECT 1 TRUNCATE
   TABLE t` → ddl, `SELECT 1 DELETE FROM t` → mutation); **`GO` 구분**
   (`SELECT 1 GO TRUNCATE TABLE t` → ddl, `GO` 단독 문장 → unknown).
3. batch: `SELECT`+`INSERT` 혼합 → mutation; read+unknown 혼합 → unknown(강등
   금지); rollback 포장 INSERT → mutation; 순서 변경이 class를 바꾸지 않음(L195);
   **mutation+unknown 혼합 batch는 `unknown`**(test 쓰기 세션에서도 거부 —
   P-5의 failure 표 9행 보수적 판독, T-4 8단계와 정합).
4. CTE: `WITH x AS (SELECT..) SELECT..` → read; `WITH x AS (..) INSERT..` →
   mutation; 괄호 내 세미콜론 무시.
5. 정규형/redaction: literal 마스킹으로 값이 달라도 hash 동일; 구조 다르면 hash
   상이; preview 200자 절단; 주석 제거 확인; 원문의 literal 값이 normalized_sql/
   preview에 부재(sentinel 단언).
6. 빈/whitespace/주석만 있는 batch의 처리 정의(빈 문장 제거; 결과적으로 0문장 →
   `unknown`으로 거부 — 모호한 것은 거부).

### T-3 — `connectors/`: engine 커넥터 + identity probes

**대상 파일**: `scripts/db/connectors/base.py`·`mssql.py`·`postgresql.py`(신규),
`scripts/tests/test_db_connectors.py`(신규). 선행: T-0(테스트 중 probe-SQL 분류
검증은 T-2 완료 후 가능).

`base.py`(driver import 없음 — 공유 타입만):

```python
@dataclass(frozen=True)
class AttestedIdentity:
    engine: str           # ENGINE_MSSQL / ENGINE_POSTGRESQL (connection_profiles 상수)
    server_identity: str
    database_identity: str

class EngineConnector(Protocol):
    engine: str
    def connect(self, connection_value: str, *, driver=None, timeout_s: float | None = None): ...
    def identity_probe(self, connection) -> AttestedIdentity: ...
    def fetch_one(self, connection, sql: str, params=None): ...
    def fetch_all(self, connection, sql: str, params=None): ...
    def execute(self, connection, sql: str, params=None) -> int: ...   # rowcount
    def close(self, connection) -> None: ...
```

`mssql.py` / `postgresql.py`(P-7):

- `driver=None`이면 사용 시점에 lazy import(`import pyodbc` / `import psycopg`) —
  `ImportError`는 `ConnectorError`(비밀 미포함: 모듈 이름만)로 변환. **top-level
  driver import 금지** — 테스트 환경에 driver가 없어도 import 가능해야 함과 동시에
  T-5 경계 검사의 connector 디렉터리 예외가 "실제로 lazy"임을 유지.
- probe(MSSQL): `SELECT @@SERVERNAME`(server) / `SELECT DB_NAME()`(database).
  probe(PostgreSQL): `SELECT current_database()` / server는 연결 객체의 host·port
  속성 → `"host:port"` 문자열. engine은 connector 상수로 반환(L150 비교용).
- **probe 결과 형태 무결성**(connector 책임): 결과 0행·NULL·빈 문자열·예상 밖
  열 구성은 `ConnectorError`로 승격 — "값을 얻지 못함"(probe-failure)과 "값은
  있으나 예상과 다름"(attestation-mismatch)을 섞지 않는다(설계 L154가 둘 다
  차단하므로 안전에는 동일하나, 이유 분리가 audit/진단 정확성의 요건이고
  guard의 형태 재검증과 이중이 된다). 또한 engine attestation의 실제 증거는
  **엔진별 방언 probe가 성공한 사실 자체**다 — connector 선택이 profile.engine
  에서 나오므로 상수 비교는 자기일치적이고, 잘못된 엔진에 연결되면 방언 probe
  (`@@SERVERNAME` ↔ `current_database()`)가 실패해 probe-failure로 차단된다.
  이 메커니즘을 주석·테스트로 명시한다(§6 failure 표 4행 참조).
- probe·fetch·execute는 `params`를 positional placeholder 전용으로 driver에
  전달(문자열 보간 금지 — SQL 합성 우회 경로 차단).
- `connect`는 connection 객체를 반환하되 그 객체는 **guard 내부에서만** 사용되며
  세션 밖으로 나가지 않는다(T-4 강제 + T-5 정적 검사 이중 방어).

테스트(`test_db_connectors.py`, fake driver/connection 객체 주입):

1. 모듈 import 후 `sys.modules`에 `pyodbc`/`psycopg` 부재(top-level import 부재
   증명).
2. fake driver 주입 시 `connect` 동작; `driver=None` 환경에서 driver 부재 →
   `ConnectorError`(비밀 미포함 단언).
3. probe가 fake 질의 기록을 남기고 `AttestedIdentity` 반환 — MSSQL probe SQL이
   정확히 `@@SERVERNAME`/`DB_NAME()` 질의; PG probe가 `current_database()` 질의 +
   연결 속성 사용.
4. **probe SQL이 전부 `read`로 분류됨**(`classify_batch` 소비 — probe 자체가
   위험 분류로 드리프트하면 guard 스스로를 막는지 확인).
5. `execute`가 driver cursor를 호출해 rowcount 반환; `params`가 placeholder로
   전달됨(보간 부재).
6. `ConnectorError` 메시지에 연결 값 sentinel 부재.
7. **probe 형태 무결성 3분화**: fake probe가 (i) 예외·timeout → `ConnectorError`
   (probe-failure 경로), (ii) 0행·NULL·빈 문자열·열 구성 이상 반환 →
   `ConnectorError`(probe-failure 경로 — mismatch 아님), (iii) 정상 형태지만
   예상과 다른 값 반환 → `AttestedIdentity` 그대로 반환(값 비교·차단은 guard의
   attestation-mismatch 경로 — connector는 값 판단하지 않음)의 세 경로가
   구분됨. (iii)에서 `""`가 아닌 이상한 값이 그대로 흘러가는 것이 올바른 동작
   (guard P-4 비교가 차단).

### T-4 — `db_guard.py`: 세션·attestation·capability 강제·audit

**대상 파일**: `scripts/db/db_guard.py`(신규),
`scripts/tests/test_db_guard.py`(신규). 선행: T-1, T-2, T-3.

공개 인터페이스(P-2/P-6):

```python
class GuardBlockedError(Exception):
    reason: str   # 고정 enum: unknown-profile | resolution-failure |
                  # missing-target-metadata | attestation-mismatch | probe-failure |
                  # capability-mismatch | privileged-denied | unknown-denied |
                  # hazardous-on-readonly | classifier-failure | audit-failure

def open_readonly(profile_name: str, *, tool_id: str,
                  allowed_profiles: Collection[str] | None = None,
                  environ=None, connector_overrides=None, metadata=None,
                  audit_sink: Callable[[str], None] | None = None) -> ReadOnlySession
def open_test_readwrite(...) -> TestWriteSession   # 동일 keyword-only 인자

class ReadOnlySession:    # fetch_one / fetch_all / close + context manager 만 공개
class TestWriteSession:   # fetch_one / fetch_all / execute / close + context manager
```

내부 흐름(설계 L204–216의 11단계를 그대로 코드 순서로):

1. `tool_id` 빈 값 거부(audit 필드 L296).
2. `open_test_readwrite`는 `operation="write"`로, `open_readonly`는
   `operation="read"`로 #23 resolver 호출 — `ProfileResolutionError`는
   `GuardBlockedError(reason="resolution-failure"/"unknown-profile")`로 래핑(메시지
   비밀 부재 보존).
3. `open_test_readwrite`: `profile.environment == test` ∧
   `profile.capability == read-write` 재확인(`PROFILES` 기준 — L147–148; registry
   미래 변경에 대한 fail-closed).
4. `get_expected_target` — 미해결/부재 → `missing-target-metadata` 차단.
   **추가로 세션 개방 경로에서 레지스트리 전체 모양 검증(T-1
   `validate_target_metadata` M1–M4)을 실행한다**(3-entry 레지스트리라 상수
   비용 — 첫 개방 시 1회 검증 후 캐시). 이 배선이 없으면 "레지스트리 test
   값과 env 연결값이 **둘 다** prod를 가리키는 이중 오구성"에서 attestation이
   일치(통과)해 버린다 — 설계 L122가 "Configuration/**preflight rejects
   execution** when ... a test target identity equals an approved production
   identity"로 요구하는 것은 바로 이 실행 시점 차단이며, 정적 검증·CI만으로는
   배치된 상태를 보호하지 못한다. 모양 결함 발견 → `missing-target-metadata`
   차단(acceptance 13.7의 잔여 우측 케이스, 테스트 추가).
5. engine 매핑 커넥터 선택(`connector_overrides`는 테스트 주입용; 기본은 engine→
   connector 고정 매핑) → `connect` → `identity_probe` → `AttestedIdentity`.
6. attestation(P-4): 먼저 `AttestedIdentity` **형태 재검증**(engine/server/
   database가 전부 None 아닌 비빈 문자열 — 위반 → `probe-failure`로 취급;
   connector(T-3)와 guard 양쪽에서 확인하는 이중 방어) 후 engine ==
   profile.engine, server/database `strip()` 정확 일치 — 불일치 →
   `attestation-mismatch`; probe 예외/timeout/형태 위반 → `probe-failure`.
   세 경로(형태 무결성·값 불일치·probe 실패) 전부 차단임을 각각 별도 테스트로
   증명(L154). `open_test_readwrite`의 개방 차단 시 audit 이벤트 발행(P-6).
7. 세션 생성. 세션은 connector·connection·expected target을 **private**으로만
   보유 — 공개 속성은 메서드뿐(`connection`/`cursor`/`driver`/`connector` 등의
   공개 속성 부재를 테스트로 고정).
8. 세션 메서드(실행 시점): SQL → `classify_batch` — 분류기 내부 예외는
   `classifier-failure` 차단(L372 "cannot decide → block"). `ReadOnlySession`:
   class != `read` → `hazardous-on-readonly`/`privileged-denied`/`unknown-denied`
   차단 + audit(outcome=blocked) — **driver 호출 전**(L369; fake driver 호출
   기록 0으로 증명). `TestWriteSession.execute`: `privileged`/`unknown` → 차단 +
   audit; 그 외(read 포함) → pre-audit(outcome=allowed) → sink 실패 시
   `audit-failure`로 실행 취소(L373) → driver `execute` → post-audit
   (succeeded/failed). fetch 계열은 양 세션 공통 read 경로(RO와 동일 규칙).
9. audit 이벤트(P-6): 단일 줄 JSON, 필드 = `timestamp`(UTC ISO)·`tool_id`·
   `profile_id`·`engine`·`environment`·`capability`·`attested_server_identity`·
   `attested_database_identity`·`operation_class`(세션 개방 차단은 `null`)·
   `sql_preview`(redacted)·`statement_hash`·`outcome`(allowed|blocked|succeeded|
   failed)·`reason`(해당 시). 기본 sink = stderr. 파라미터 값·연결 값·row 값은
   어떤 필드에도 존재할 수 없다(구조적으로 — preview/hash 원천이 T-2 정규형뿐).
10. 우회로 부재(L322–334 금지 메커니즘 7종 **각각**에 구조적 방지 + 그 방지를
     증명하는 테스트 — 총칭만이 아니라 대응 증명):
     - `--force-production-write` / `--unsafe` / "type YES" 확인 프롬프트(3종):
       guard는 CLI가 없는 라이브러리(P-2) — 모듈 소스에 `argparse`/`sys.argv`
       접근·`input(` 호출이 부재함을 소스/AST 검사 테스트로 고정(금지 메커니즘이
       **존재할 수 없는 표면**에 있다는 사실의 기계화).
     - attestation 무효화 env: guard 자체 환경변수가 없음 — 모듈이
       `os.environ`/`os.getenv`를 직접 읽지 않음(`environ`은 #23 resolver
       전달뿐)을 소스/AST 검사 테스트로 고정.
     - `unknown`→`read` 재분류 플래그: 공개 시그니처가 P-2 고정 집합 그대로임을
       `inspect.signature` 정확 일치 테스트로 고정(우회 파라미터 추가 자체가
       테스트 실패 — `open_readonly`/`open_test_readwrite`·`classify_batch`
       전부). 세션 메서드에 재분류 인자 부재도 동일 단언.
     - caller raw connection string: 인자는 profile 이름뿐이고 연결 값은 #23
       resolver의 env 매핑에서만 나옴 — signature 테스트 + "연결 값은
       `ResolvedProfile.connection_value` 경유로만 connector에 도달" 단언
       (P-2: 주입 인자는 I/O 대체일 뿐 검사 우회 불가 — attestation이 어떤
       경로로 들어온 값에도 동일 적용).
     - raw cursor/connection 노출: 세션 private 속성(7단계 공개 표면 테스트) +
       모듈 재수출 부재 테스트 + T-5 B2 정적 차단(3중).
     우회로 부재 총칭 확인: 어떤 함수·플래그·env도 attestation/allowlist/차단을
     무효화하지 않음 — `db_guard` 모듈이 driver·connector 심볼을 재수출하지
     않음을 테스트로 고정.

테스트(`test_db_guard.py`) — acceptance 13개 + failure 표 11행의 1:1 매트릭스(§6
표 참조). fake connector는 probe 결과·질의 기록을 scriptable하게, env sentinel
(`"mssql://user:SECRET-VALUE@..."`)과 파라미터 sentinel을 심어 전 audit 출력·
오류에서 부재 단언. "차단이 driver 실행 전" 증명은 fake의 execute 호출 목록이
비었음으로.

### T-5 — `validate_scaffold.py`: driver/connector import 경계 정적 검사

**대상 파일**: `scripts/validate_scaffold.py`(신규 독립 함수 + 상수),
`scripts/tests/test_db_driver_boundary.py`(신규). 선행: T-0.

- 신규 상수(`validate_env_example_contract` 인근 관례):
  `BANNED_DRIVER_ROOTS = ("pyodbc", "pymssql", "psycopg", "psycopg2",
  "sqlalchemy", "asyncpg", "pg8000", "adodbapi")`(마지막 3종은 비동기 PG·
  pure-Python PG·Windows ADO 경로 — 열거에서 빠지면 B1 자체가 우회로가 됨,
  P-8), `CONNECTORS_PACKAGE = "scripts.db.connectors"`,
  `CONNECTORS_ALLOWED_IMPORTERS = ("scripts/db/db_guard.py",)` +
  `CONNECTORS_TEST_EXCEPTIONS = ("scripts/tests/test_db_connectors.py",)`(열거 —
  L353; 파일명·의도 추론 금지, 추가는 design change).
- 신규 독립 함수 `validate_db_driver_boundary(root: Path | None = None) ->
  list[str]`, `ast.walk` 기반(P-8):
  - B1: `scripts/**/*.py` 중 `scripts/db/connectors/**` 밖에서 `BANNED_DRIVER_ROOTS`
    의 import(`import X`/`from X import`/`from X.Y import` 전 형태).
  - B2: `scripts.db.connectors` 패키지 import가 허용 importer(db_guard·connectors
    내부)·열거 테스트 예외 밖에서 발견됨(finding 9의 guard 우회 경로).
    **상대 import 형태를 결정적으로 해석**한다 — `from . import connectors`,
    `from .connectors import mssql`, `from ..db.connectors import x` 등
    `level >= 1`의 `ImportFrom`은 해당 파일 위치 기준으로 절대 경로화하여
    판정(문자열 `"scripts.db.connectors"` 등장만 검사하면 상대 형태가 전부
    누락된다).
  - B3: **동적 import 통로 차단** — `scripts/db/connectors/**`·열거 예외 밖의
    `scripts/**/*.py`에서 `importlib` import/사용(`import_module` 등) 또는
    `__import__` 내장 호출이 발견되면 위반. AST import 검사는 정적 import만
    보므로 이 통로를 별도 금지하지 않으면 `importlib.import_module("pyodbc")`
    한 줄로 B1이 무력화된다. 현재 `scripts/` 전체에서 `importlib`·`__import__`
    사용 0건(본 세션 grep 확인)이고 connectors의 lazy import는 함수 내 일반
    `import` 문으로 충분하므로 예외 열거 추가 없는 전면 금지가 결정적 규칙이다.
  - 진단 형식 `path:line [db-driver-boundary] message` 관례.
- 배선: `main()` errors 통합에 추가(기존 검사·섹션 무변경 — #23 T-2와 동일
  최소 확장)하는 데 2건: (1) `validate_db_driver_boundary()` 상기 B1–B3;
  (2) **T-1 `validate_target_metadata()`(M1–M4) 결과** — P-3에 따라
  expected-target **값은 in-code로 커밋**되므로 모양 결함(prod/test 충돌 포함)은
  CI에서 결정적으로 잡힌다(런타임 preflight T-4 4단계와 이중 방어: 사용자의
  값 공급 실수가 merge 전에 발견된다). CI workflow 파일 무변경(`repo-guards`가
  자동 승계).
- 테스트(`test_db_driver_boundary.py`, `tmp_path` 합성 fixture 패턴): B1 양성
  (합성 `scripts/foo.py`에 `import pyodbc`)·각 driver root 8종(신규 3종 포함)·
  `from psycopg2 import connect` 형태, connectors 디렉터리 내부는 허용, B2 양성
  (합성 도구 파일의 `from scripts.db.connectors import mssql` **및 상대 형태**
  `from .connectors import mssql`·`from . import connectors`)·허용
  importer(db_guard)는 green·열거 테스트 예외 green·예외 밖 테스트 파일은
  위반, B3 양성(합성 파일의 `import importlib`·`importlib.import_module(
  "pyodbc")`·`__import__("pyodbc")` 각각 위반 — connectors 내부·열거 예외
  파일은 green), 배선 (2) 양성(합성 targets 충돌 → validator errors 반영),
  실제 저장소 green(현 시점 무검출 상태 + T-4 완료 후에도 green).

### T-I1 — 통합 검증

- `python3 scripts/validate_scaffold.py` exit 0(신규 경계 검사가 기존 전 검사와
  공존 — 실제 저장소가 T-1..T-4 산출물 위에서 green).
- `python3 -m pytest scripts/tests/ -q` 전수 통과(434 baseline + 신규 전체).
- `check_doc_links.py`, `check_oq_updates.py` green(OQ-014·OQ-021 상태 무변경).
- 비범위 무변경 확인(`git diff`): `docs/12-*` 2건·`scripts/db/connection_profiles.py`·
  `.env.example`·`.gitignore`·`target/backend`·CI workflow·#18/#19/#21/#22 관련
  파일 전부 무변경.
- 무단 import 부재: `scripts/db/connectors/` 밖에서 driver import 부재(T-5가
  기계 강제 + grep 재확인), `connection_profiles.py` 재정의 부재(#23 상수는 import
  소비만).
- 미달 시 수정 후 재실행.

### T-R1 / T-R2 — 독립 adversarial review 1차·2차 (구현자와 독립, AGENTS.md rule 10)

각 회차 fresh subagent, #6/#9/#11/#23 확립 패턴(1단계: PR 제목/본문만 보고 반증
가능 가설 작성 → 2단계: diff/repo 접근 + validator/pytest 직접 실행으로 가설
검증). **2회 예산은 HANDOFF 명시 의무**("budget for at least two independent
review passes before treating it as mergeable"). 점검 초점:

- (a) **분류기 우회 공격**(finding 1/2의 실증): 주석·문자열·식별자 quote·중첩·
  대소문자·batch 구분자·`EXEC` 생략형·`SELECT INTO` 변형(CTE 본문 포함)·
  data-modifying CTE·구분자 없는 다중 문장·GO — 리뷰어가 신규 변형을 직접
  시도해 `read` 오인정·hazardous 누락을 탐색. `unknown` 강등 경로 전수 확인
  (L194; **test 쓰기 세션에서의 unknown 거부 포함** — P-5의 failure 표 9행
  보수적 판독).
- (b) **"checks the shape, not the substance" 계열**(PR #66/#67/#68 3연속 패턴):
  T-5 경계 검사의 과소강제(신규 변형 탐색 — 상대 import 해석 누락, B3 우회
  시도; B2/B3는 이제 결정적 검사이므로 리뷰어는 규칙 적용 오류가 아니라
  **미열거 통로의 신규 발견**을 탐색), T-1 모양 검증의 우회(공백·유니코드
  정규화 회피) **및 런타임 배선 누락**(T-4 4단계 전체 검증이 실제 open
  경로에서 호출되는지 — 정의만 있고 안 쓰이면 이중 오구성 차단이 무력화됨),
  T-4 audit 필드 누락·sentinel 변형.
- (c) **비밀 누출 탐색**: audit 전 필드·오류 전 경로·`repr`/`str`/traceback에서
  연결 값·파라미터·row sentinel 부재(변형 sentinel 시도 포함).
- (d) **capability 우회 탐색**: 세션 공개 속성·`__getattr__`·module 재수출·
  connector 직접 import·private 접근 시도; `open_test_readwrite`가 attestation
  없이 세션을 반환하는 경로 부재.
- (e) **P-항목 유도 정합성**: P-1..P-12 각 항목이 설계 줄 인용 그대로인지 —
  근거 없는 신규 lock-in(예: 분류기 완화, 메타데이터 표현 변경, 예외 열거 확장)은
  §5 트리거로 승격.
- (f) **Non-goals/비범위 준수**: 게이트 5 목록 대로; 특히 #18/#19/#21/#22 도구·
  materialization 개념·parser 의존성·`--force`류 부재.
- T-R2 종료 후 **소유자 수준 패스** 1회 추가 예산(HANDOFF: 신규 validator 초회
  과소강제가 3연속 발견된 계열 — fix 커밋 자체에 대한 재검 포함).

발견 사항은 수정 후 re-verify(수정 커밋마다 대상 테스트 재실행 + 전수).

### T-H1 — HANDOFF 갱신 + Issue 코멘트 + PR

- `HANDOFF.md` in-place 갱신: 근거 SHA·테스트 수·리뷰 2회 결과·소비 안내
  (`from scripts.db.db_guard import open_readonly, open_test_readwrite` — #18/#22
  및 이후 #19/#21 소비용)·**잔여 불확실성 명시**: (1) expected-target 실제 값은
  미해결 상태로 출하 — 실제 세션 개방은 사용자가 배포 사실을 공급할 때까지
  fail-closed 차단(의도된 상태, P-3), (2) 실제 MSSQL/PostgreSQL 연동 검증은
  승인된 테스트 인프라 확보 후 별도 수행(L421), (3) 소비 도구 배선은 각 이슈
  범위(P-10), (4) **AC2의 server-enforced read-only production credential
  provisioning은 사용자 배포 사실**이다(L95: guard는 쓰기 시도로 검증 금지 —
  런타임 증명 불가) — expected-target 값과 함께 provision 사실 확인을 요청하고
  회신을 기록한다(P-9).
- Issue #20에 구현 코멘트(게이트 결과 요약 + acceptance 13개 매핑 + expected-target
  값 공급 요청 안내).
- PR 개설 + 리뷰 코멘트 게시 후 **사용자의 명시적 merge 지시 대기**(2026-08-22
  워크플로 변경, #65/#66/#67/#68 선례). merge 직전 `git log <base>..HEAD` 재확인
  (#13 세션 타이밍 레이스 선례). merge 후 소유자 post-merge 리뷰가 끝나기 전에는
  #20을 완료로 간주하지 않는다.

병렬성 요약: 그룹 A(T-1/T-2/T-3/T-5)는 파일 소유권 완전 분리로 병렬 가능. 단일
세션 실행 시 순서 권장: T-2 → T-1 → T-3 → T-5 → T-4(T-4가 소비하는 인터페이스
순서대로; T-5는 어느 시점이든 무관하나 실제 저장소 green은 T-4 완료 후 성립).

---

## 5. 설계 게이트 재오픈 트리거 (구현/리뷰 중 하나라도 걸리면 중단하고 기록)

1. **materialization 개념 필요성 발견.** guard 구현이 #19의 manifest/allowlist/
   masking/consistency 개념을 요구하는 것으로 판명되면(P-11 판정 붕괴) 즉시 중단
   — 사용자에게 #19 재오픈 여부(또는 #20 범위 축소)를 질의한다(상위 계획 L102).
2. **expected-target 실제 값이 필요해 보이는 순간.** 값은 사용자 공급 배포 사실
   (L386) — 구현자/리뷰어/에이전트 누구도 추측으로 채우지 않는다. 테스트는 합성
   값으로만.
3. **hard driver 의존성·dependency manifest 신설이 필요해 보이는 경우.** P-7의
    lazy import로 부족하다고 판명되면 신규 lock-in — 질의 후 결정(PR #58 P2 선례).
4. **SQL parser가 필요하다고 판단되는 경우.** L427 Non-goal 위반 — tokenizer
   보수성으로 부족한 사례를 기록하고 게이트 재개방. "나중에 parser를 쓰면 parser
   실패는 차단"(L198)은 이미 본 계획의 fail-closed 원칙과 일치.
5. **분류기 완화 요구.** 소비 도구가 transaction 제어/`SET` 등 `unknown` 항목을
   필요로 하게 되면 그것은 허용 목록 확장이라는 정책 변경이다(L190–198 영역) —
   임의 완화 금지.
6. **두 번째 프로필 메타데이터 경로·설정 파일 요구.** L120/#23 finding 1 위반.
7. **우회로 요구.** `--force`·`--unsafe`·확인 프롬프트·attestation 무효화 env·
   `unknown` 강등 플래그·raw connection 노출(L322–334) — 어떤 형태로도 제공하지
   않는다. 요구 자체가 발생하면 그것은 별도 운영 절차 설계 질문(L334).
8. **#23 resolver API 부족 발견.** 신규 파라미터·속성 확장은 #23 설계 변경 —
   #23 게이트와 함께 재개방(#23 실행계획 트리거 5와 대칭).
9. **경계 검사 예외·금지 목록 변경 요구.** `CONNECTORS_TEST_EXCEPTIONS` 등 열거
   추가와 `BANNED_DRIVER_ROOTS`의 확장·축소는 전부 design change(L353 — 금지
   목록은 "직접 driver import" 일반 계약의 구체화일 뿐) — 리뷰에서만
   정당화하지 않고 기록 후 승인.
10. **FastAPI `target/backend`에 대한 적용 범위 질문.** L355가 자동 적용을 명시
    제외 — 그 층의 정책은 별개 설계. 검사 범위를 `target/`로 확대하지 않는다.
11. **audit 필드·redaction 규칙의 충돌 발견.** 예: sink 실패 의미론(L373)과 세션
    개방 audit(P-6)의 상호작용에서 설계가 정하지 않은 모호성이 실제 결함을 만들면
    docs/12 수준 질문으로 재개방.

재개방 시 취할 행동: 해당 design gate(#20 또는 충돌하는 타 이슈 설계)을 열고
`docs/05-open-questions.md` 또는 이슈 코멘트로 미결정 사항을 기록한 뒤 사용자
판단을 기다린다. 임의 결정 금지.

---

## 6. 검증/완료 기준

설계 acceptance criteria(L394–419) → 구현 매핑:

| 설계 완료 기준 (요지) | 담당 |
|---|---|
| 1. #23 resolver 소비, 두 번째 비밀/설정 경로 부재 (L394) | T-4 2단계(resolver 호출) + 게이트 5 비변경 목록 + T-R1/T-R2 (f) — `connection_profiles.py` 무변경 |
| 2. 서버단 read-only 계정 문서화·과권한 prod credential 결함 취급 (L395) | P-9 — 런타임 코드 없음(L95 검증 금지). docs/12 자체(L83–97)가 문서화 담당(`.env.example` 주석은 capability만 기술 — P-9 확인). **T-H1에서 provision 배포 사실 확인을 사용자에게 전달·수집** + T-4가 계정 권한과 무관하게 차단(L240)하는 테스트 |
| 3. 모든 canonical profile에 명시적 expected server/database identity 메타데이터 (L396) | T-1 레지스트리(key 정합 테스트) + 미해결 값의 fail-closed(P-3) — 구조 존재와 값 공급 분리 + **open 경로 전체 검증 배선(T-4 4단계)·CI 배선(T-5)** |
| 4. 모든 개방 세션이 사용 가능해지기 전 engine/server/database attestation (L397) | T-4 5–6단계 + 테스트(prod read도 attestation 필수 — L156 케이스 포함) |
| 5. 쓰기 capability는 canonical test+read-write + 정확한 attestation 뒤에만 (L398) | T-4 3·6단계 + 테스트(불일치·미해결·prod 지목 전부 차단) |
| 6. prod/read-only 세션에 범용 mutation 실행 API 부재 (L399) | T-4 `ReadOnlySession` 공개 표면(fetch만) + 공개 속성 부재 테스트 |
| 7. 저장 프로시저 실행은 기본 위험·prod 도달 불가 (L400) | T-2 `procedure-exec` 매핑 + T-4 RO 차단 테스트(이름이 read-only처럼 보여도 — finding 6) |
| 8. mutation/DDL/procedure/unknown/rollback 포장/위험 혼합 batch의 prod 불가 (L401) | T-2 batch 규칙 + T-4 차단 테스트(전 항목 개별 케이스) |
| 9. 위험 실행의 pre-execution audit — 대상/profile/연산 identity 포함, 연결 값·비밀·파라미터·row 값 부재 (L402) | T-4 audit 이벤트 + sentinel 테스트(전 필드) |
| 10. routine runtime override 부재 (L403) | T-4 10단계 — **금지 메커니즘 7종(L326–332) 각각의 구조적 방지 + 테스트**(CLI/프롬프트 부재 소스 단언, env 직접 읽기 부재, signature 고정, 연결 값 resolver 경유, raw 노출 3중 차단) + T-R1/T-R2 (d) |
| 11. #18/#19/#21/#22가 공통 경계 소비 (L404) | **이후-소비 기준**(P-10) — 공개 API·경계 강제 제공으로 충족, 실제 배선은 각 이슈 완료 기준 |
| 12. CI/동등한 결정적 검사가 무단 직접 driver/연결 사용 탐지 (L405) | T-5(B1/B2)가 `repo-guards` CI에서 상시 강제 |
| 13. 테스트 13개 시나리오 (L406–419) | 아래 표 |

Acceptance 13 시나리오(L407–419) → 구체 테스트:

| # | 시나리오 | 테스트 위치 |
|---|---|---|
| 13.1 | `mssql-prod-ro` read 허용(정확한 identity attestation 후) | test_db_guard(fake connector 일치 케이스) |
| 13.2 | prod mutation이 driver 실행 전 차단 | test_db_guard(fake driver 호출 기록 0 단언) |
| 13.3 | prod DDL 차단 | test_db_guard |
| 13.4 | prod procedure 실행 차단 | test_db_guard |
| 13.5 | 명시적 rollback transaction으로 포장해도 prod mutation 차단 | test_db_guard(T-2 batch 규칙과 결합) |
| 13.6 | `mssql-test-rw` mutation은 정확한 test identity 일치 후에만 허용 | test_db_guard(허용·불일치 양쪽) |
| 13.7 | test profile이 prod identity를 가리키면 차단 | test_db_guard(attestation mismatch) + T-1 M2(레지스트리 정적 충돌) + **이중 오구성 케이스**(레지스트리 test 값 = prod 값 ∧ env도 prod 연결 → attestation은 일치하나 T-4 4단계 전체 검증이 충돌로 차단 — L122 preflight 요구의 잔여 우측) |
| 13.8 | source/target identity 충돌 차단 | T-1 M2/M3 + test_db_guard(쌍 일치 차단) |
| 13.9 | missing/ambiguous target identity 차단 | test_db_guard(미해결 메타데이터) + T-1 2번 |
| 13.10 | 혼합 read/write batch가 read로 강등되지 않음 | test_db_guard(RO 차단; TestWriteSession — **unknown 미포함 혼합 batch만 허용, unknown 포함은 test에서도 차단**, P-5 보수적 판독) + test_db_sql_classification 3번 |
| 13.11 | 분류기 실패가 허용이 아니라 차단 | test_db_guard(monkeypatch로 분류기 예외 유발 → `classifier-failure` 차단) + T-2 unknown 케이스 |
| 13.12 | audit 출력에 연결 값·자격증명·파라미터·row 값 부재 | test_db_guard(sentinel 단언 — env·params·rows) |
| 13.13 | 통상 도구가 raw writable connection을 얻거나 사용해 guard를 우회할 수 없음 | test_db_guard(공개 속성·module 재수출 부재) + T-5 B2 + T-R1/T-R2 (d) |

Failure behavior 표(L361–373) 11행 → 테스트:

| 조건 | 결과 | 테스트 |
|---|---|---|
| unknown/non-canonical profile | block | test_db_guard(`resolution-failure`/`unknown-profile`) |
| #23 해결 실패 | block | test_db_guard(env unset/empty/whitespace → 래핑 오류 + **`allowed_profiles` 전달 위반 케이스** — guard 도달 가능한 resolution 실패 유형 전부; unknown profile은 1행, write×RO는 6행) |
| missing/ambiguous expected target | block | test_db_guard(미해결 값 + **모호(prod/test·test/test 쌍 일치) 케이스가 open 경로 전체 검증(T-4 4단계)에서 차단** — 정의만 있고 배선 안 된 상태를 리뷰가 못 잡으면 이중 오구성 뚫림) + T-1 |
| 실제 engine/server/database 불일치 | block | test_db_guard(server·database 불일치 → `attestation-mismatch`; **engine 불일치는 방언 probe 실패로 구현**돼 `probe-failure`로 차단 — T-3 engine attestation 메커니즘 참조. 차단 자체가 요구이므로 reason enum 구분은 진단 정확성 문제) |
| probe 실패 | block | test_db_guard(fake probe 예외/timeout + **결과 0행·NULL·빈 값·형태 이상 → `probe-failure`**, mismatch와 구분 — T-3 7번) |
| 쓰기 요청이 canonical test+rw 아님 | block | test_db_guard(`open_test_readwrite("mssql-prod-ro")` → resolver+3단계 이중 차단) |
| RO 세션의 위험 연산 | driver 실행 전 차단 | test_db_guard(호출 기록 0) |
| prod에서 procedure 실행 | block | test_db_guard |
| 혼합 batch | prod 차단 / test는 attested write 세션 필요 | test_db_guard 양쪽(RO 차단; TestWriteSession — **unknown 미포함 혼합 batch만 허용, unknown 포함은 test 쓰기 세션에서도 차단** — P-5의 보수적 판독, 조건 열의 `unknown` 포함을 L188/L194/L372 기준으로 해석) |
| 분류기 판단 불능 | block | test_db_guard(`classifier-failure`) + T-2 |
| 위험 pre-audit 발행 불능 | 위험 실행 차단 | test_db_guard(sink 예외 → `audit-failure`, 실행 안 됨) |

추가 완료 기준:

- `python3 scripts/validate_scaffold.py` exit 0 — 신규 경계 검사가 기존 전 검사와
  공존, 실제 저장소 green.
- `python3 -m pytest scripts/tests/ -q` 전수 통과(434 baseline + 신규).
- `check_doc_links.py`, `check_oq_updates.py` 통과(OQ-014·OQ-021 무변경).
- **독립 리뷰 2회(T-R1, T-R2) + 소유자 수준 패스**가 Non-goals 위반·분류기 우회·
  과소강제·비밀 누출·우회로·P-항정 정합성 위반을 발견하지 않음(HANDOFF 의무).
- 게이트 5 비변경 목록의 `git diff` 무변경 확인(T-I1).
- Issue #20은 merge(사용자 명시 지시 후) + 소유자 post-merge 리뷰 완료 전까지
  완료로 간주하지 않는다(#61/#62/#64/#65/#67/#68 선례).

## 7. PR/merge 권장

**단일 PR 권장.** 레이어 전체(레지스트리·분류기·커넥터·guard·정적 검사)가 하나의
안전 계약 결합부다 — 분리 시 "guard 존재 + 경계 미강제" 같은 혼합 계약 상태가
발생한다(본 저장소 "no mixed-contract state" 선례, #5/#6/#9/#11/#23).

merge 순서: Track D 2번 항목. #20 merge 전에 #18/#22 core 착수 금지(Track D merge
순서 — 단 D-I 노트대로 #18은 #20을 하드 선행으로 요구하지 않으므로 착수 순서는
상위 계획 참조). 진행 중 병렬 브랜치 없음(open PR 없음 확인). 구현 브랜치는 최신
`main`에서 분기해 단일 PR로 squash-merge하되, **PR 개설 + 리뷰 코멘트 게시 후
사용자의 명시적 merge 지시를 기다린다**(2026-08-22 워크플로 변경, PR #65/#66/#67/
#68 선례). merge 직전 `git log <base>..HEAD` 재확인(#13 세션 타이밍 레이스 선례).
merge 후 소유자 post-merge 리뷰 추적, 리뷰 코멘트에는 fix 커밋 인라인 회신, 리뷰
스레드를 해결/기각하지 않음(#23 세션 확립 패턴).
