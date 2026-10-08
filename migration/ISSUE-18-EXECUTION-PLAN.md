# Issue #18 실행 계획 — MSSQL 읽기전용 운영 DB 검사 도구 (`scripts/db/mssql_inspect.py`)

작성일: 2026-10-07 / 기준 커밋: `bef5b43`(=origin/main, 워크트리 `hjung3113/issue18-plan`, diff 0)
Canonical design: `docs/issue-18-mssql-readonly-inspection.md`(309줄, 병합 `f3846b2`, 이후 무변경 — `git diff f3846b2 HEAD` 빈 출력 확인). 본 계획은 설계를 재진술하지 않고 구현만 계획한다.
Dependencies: #23 `docs/12-db-connection-secrets-contract.md` → `scripts/db/connection_profiles.py`(117줄) / #20 `docs/12-db-execution-safety-contract.md` → `scripts/db/db_guard.py`(551줄)+`connectors/`+`sql_classification.py`(668줄)+`target_metadata.py`(197줄), PR #69 squash `18f20a4`.
주의: 지시문의 리뷰 수정 커밋 `d6a9678`은 `main` 조상이 아님(본 세션 `merge-base --is-ancestor` 실패 — squash 흡수). 판정 근거는 현재 파일 내용이며 리뷰 수정(공백 attestation `db_guard.py:276-288`, privileged-target `sql_classification.py:87-90` 등)은 현행에 존재.
상위 계획: `migration/ISSUES-PLAN-DRAFT.md` D-I `#23 -> #18`(L104-110), Track D merge 3번, "#18과 #22 core 병렬 가능"(L151).
이슈: #18 본문(일부 stale — 게이트 2) + 코멘트 2건(프로필 확정, PR #51 병합 보고의 10항목 구현 범위).
프로세스 개정 반영(2026-10-07 지시): DAG 리뷰는 T-R1 단일 최종 독립 리뷰(codex gpt-6.1-sol xhigh, 구현자와 다른 모델) + 발견 일괄 수정 T-F1(conductor 검증) 1회, 2차 최종 리뷰 없음. 리뷰 전 호스트 검증(`scripts/verify.sh`) 선행. 구현 워커는 git을 실행하지 않고 conductor가 커밋한다. 형식 개정: 본 문서는 ~200행 요약 — 게이트 항목별 1줄, 판정은 근거 인용, 설계 재진술 없음.
사실 표기: 모든 사실에 `(근거: 파일:줄)`/`(본 세션 실행 확인)`, 설계 미고정 판정은 **[추론]**.

## 1. 게이트 체크 (7항목 — ISSUES-PLAN-DRAFT L178+ 템플릿)

기본 상태(본 세션 실행 확인): `validate_scaffold.py`/`check_doc_links.py`/`check_oq_updates.py` 전부 exit 0, `pytest scripts/tests/ -q` **631 passed**, open PR 없음.
- **게이트 1 통과** — 설계 309줄 + 의존 계약 2건(#23 209줄, #20 436줄) + 소비 모듈 5개 전문 읽음; 구현 판정 근거 줄은 §2-§4 인용.
- **게이트 2 통과** — 본문 stale 미채택: 연결 문자열 env 주입→#23 프로필(설계 L79-92), `sp_helptext`→`sys.sql_modules`(guard가 `EXEC`를 `procedure-exec` 차단, `sql_classification.py:493`; #20 계약 L259-261), `INFORMATION_SCHEMA` 단독→`sys.*` 중심(설계 L30), markdown paste→raw/Git 경계(설계 L33, L234-250).
- **게이트 3 조건부 통과** — 소비할 guard/resolver는 `main`에 존재하나 **M-1**: `EXPECTED_TARGETS` 전 프로필 빈 값(`target_metadata.py:41-46`)이라 `open_readonly`는 오늘 기준 항상 `GuardBlockedError("missing-target-metadata")`로 fail-closed(`db_guard.py:163-169`) — live 세션 활성화는 #20 소유 파일의 값 공급(사용자 배포 사실, #20 계약 L386)이 선행돼야 한다.
- **게이트 4 통과 (2026-10-07)** — 사용자가 계획 검토 후 "머지하고 작업이어해"로 구현 착수를 명시 승인(같은 답변에서 §6-1 PARTIAL/BLOCKED 제안 규칙 수용).
- **게이트 5 통과** — 범위 = 설계 Phase 1 조건 11개(L279-291)+CLI/출력 계약(L108-248)+코멘트 10항목 이내. 비변경: 설계 문서 3종, `scripts/db/` 기존 5모듈, `validate_scaffold.py`, CI, `.env.example`, OQ 문서, `migration/features/**`.
- **게이트 6 통과** — 재오픈 메커니즘 3중(상위 계획 원칙, rule 13, §5 트리거 11개).
- **게이트 7 통과** — open PR 없음(본 세션 확인). 공유 파일: `.gitignore`(1행만 추가), `.opencode/` 2문서(#18 단독), `HANDOFF.md`(T-H1 in-place). #22 core와 병렬 가능하나 merge 직전 최신 main 재검토(상위 계획 L88-90).

## 2. 구현 코멘트 10항목 × 현재 db_guard 정합성 판정

정합 7 / caveat 1(M-1) / 도구 측 책임 2(M-4·M-5). **실 충돌은 M-1뿐** — 임의 해소 없이 트리거로 상향.

- **M-1 [충돌→트리거 1]** 위 표 게이트 3: 세션 개방 자체가 현재 차단. 코멘트 10항목(live validation)은 expected-target 값 공급 + DBA 환경이 전제.
- **M-2 [비충돌, 의미 고정]** `--expect-database`(설계 L106) vs guard attestation(레지스트리 3중 일치, `db_guard.py:305-316`): **둘 다 수행, guard가 먼저**. 세션 개방 후 `SELECT DB_NAME()` 1회 비교, 불일치 시 inventory 전 중단(설계 문언 충족). `--expect-database`는 attestation을 완화할 수 없다 — 레지스트리 불일치는 guard가 먼저 `attestation-mismatch`로 차단하는 것이 올바른 fail-closed. 공급 여부·값은 capture context에 기록 **[추론]**(DB명은 설계 L140이 capture 항목).
- **M-3 [비충돌, 정적 증명 필요]** allowlist 질의는 전부 `read`로 분류됨(`sql_classification.py:467-469`) — 단 (a) `INTO` 토큰 전 깊이 부재, (b) 위험 동사와 동일한 비인용 식별자 부재(L504-531; `[created]` 인용 식별자는 면역, `:655-657`), (c) `USE` 배치 금지(`unknown` 차단, L92-97) — msdb는 3부 이름 질의. 레지스트리 전수 분류 테스트로 기계 고정.
- **M-4 [gap→도구 책임]** guard는 임의 `read` SELECT를 통과시킨다 — "닫힌 질의 집합"(설계 L99)은 도구 속성: 모듈 리터럴 frozenset 레지스트리 + 질의 기록 ⊆ 레지스트리 테스트 + `--sql` 인자 부재 검사. validator 신규 검사 **불요** — 기존 `validate_db_driver_boundary` B1/B2/B3(`validate_scaffold.py:941-1013`, 배선 `:3014`)가 driver/connector 직접 경로를 이미 기계 차단.
- **M-5 [비충돌, 규칙 필요]** msdb 접근 실패 → `agent_jobs` PARTIAL|BLOCKED(설계 L228, L186), 0-jobs 위장 금지. PARTIAL vs BLOCKED 경계는 설계 미고정 → P-6 규칙 + 사용자 확인(§6).
- **M-6 [비충돌]** 정의는 `sys.sql_modules` 등 카탈로그 SELECT만. definition NULL → `UNAVAILABLE`+`reason: UNKNOWN`(설계 L210-218), scope 내 존재 시 `module_definitions` 최소 PARTIAL(L227) — `ABSENT` 경로 부재를 테스트로 강제.

## 3. 파생 판정 P-1..P-13 (신규 lock-in 아님 — 근거 인용)

- **P-1 모듈 배치**: 단일 `scripts/db/mssql_inspect.py` + 단일 테스트 파일, `__init__.py` 불요. 근거: 설계 L60-65(canonical 경로·단일 책임), `scripts/db` 네임스페이스 관례. [추론] 내부 분할 최소.
- **P-2 연결**: `db_guard.open_readonly("mssql-prod-ro", tool_id="mssql-inspect", allowed_profiles=("mssql-prod-ro",), audit_sink=None)` 단일 경로, resolver/driver 직접 import 금지. 근거: 설계 L53·L279, #20 계약 L257-261, validator B1/B2. [추론] tool_id 고정 문자열.
- **P-3 질의 레지스트리**: 리터럴 frozenset(텍스트+카테고리+해석 메타), 값 필터는 `?` 파라미터, 결정론 `ORDER BY`. 근거: 설계 L99-103. [추론] V1은 값 비교 필터뿐이라 안전 식별자 조립 불요 — 필요 시 트리거 3.
- **P-4 스냅샷/버저닝**: JSON canonical, 최상위 키 `schema_version/capture/scope/capabilities/warnings/inventory`(설계 L189-199), Markdown은 동일 객체 파생(L137). `schema_version` 정수 `1` 시작, 모양 breaking 시 +1 **[추론]**. capture는 설계 L139-147 전 항목.
- **P-5 해시**: sha256(UTF-8 원문 전문), `definition_sha256`는 AVAILABLE일 때만. 근거: 설계 L215 필드명, L172. [추론] 정규화 없는 원문 해시(원문이 증거).
- **P-6 completeness 산정**: 결정론 순수 함수 — 전 질의 성공+가시성 전제 성립+unavailable 0이면 COMPLETE, 일부 실패/숨은 정의 존재면 PARTIAL(설계 L222-227), 1차 원천 전체 불가 BLOCKED, 플래그 부재 NOT_REQUESTED. **PARTIAL vs BLOCKED의 데이터 유무 분해는 [추론]**(설계 L228 "PARTIAL or BLOCKED" 미고정) → §6 확인 항목.
- **P-7 `.gitignore`**: 1행 `.local/mssql-inspection/` 추가. 근거: 설계 L130(구현 의무). [추론] `.local/` 전체가 아닌 필요 최소폭; `--output-dir` 사용자 override의 Git 추적 경로는 도구가 막지 않음(기본값만 비-Git 요구).
- **P-8 CLI**: argparse, `snapshot` 전용, 플래그 설계 L108-121 그대로, `--include-job-step-text`는 `--include-jobs` 없이 오면 연결 전 오류(L128). [추론] 종료 코드 0/1(입력)/2(차단·DB 불일치), `--format` 기본 json.
- **P-9 stdout 경계**: 짧은 비밀 아닌 요약만(capture-id·scope·카테고리 상태·warnings), 원문·job-step 텍스트·연결값 출력 금지. 근거: 설계 L131-132.
- **P-10 OMITTED_BY_POLICY**: enum에 예약, V1 코드 경로는 생성하지 않음. 근거: 설계 L210-216(enum 지정) vs L108-121(raw 생략 플래그 부재). [추론] durable store 연계 시 의미(설계 L248).
- **P-11 capture-id**: UTC 타임스탬프+uuid4 단편(디렉터명=`capture.id`=stdout 요약 동일값). 근거: 설계 L130·L140. [추론] 형식 미지정 최소 조합.
- **P-12 배포 사실 공백**: expected-target 값 주입·live 자격은 본 구현 범위 아님 — 테스트는 patch seam(`test_db_guard.py:74-118` 선례). 근거: #20 계약 L386, M-1.
- **P-13 문서 경계**: inspector를 canonical live-MSSQL evidence path로 명명 + completeness-먼저-해석 + raw 복사 금지 3계열만 추가; read-only specialist → coordinator persistence 규칙·STOP payload·generated 블록 무변경. 근거: 설계 L256-268, 기존 문서 경계 문구.

## 4. 태스크 분해 (DAG)

```text
T-0 (완료: 본 문서) 게이트+정합성 판정+계획 작성·커밋
     v
[병렬 A: 파일 분리] T-1(mssql_inspect.py+테스트) ∥ T-2(.opencode 2문서) ∥ T-3(.gitignore)
     v
T-V 호스트 검증 (scripts/verify.sh: scaffold/OQ/doc-links/pytest) — 리뷰 선행 필수
     v
T-R1 단일 최종 독립 리뷰 (codex gpt-6.1-sol xhigh — omp 구현자와 다른 모델)
     v
T-F1 발견 일괄 수정 1라운드 → conductor가 재검증 (2차 최종 리뷰 없음)
     v
T-H1 HANDOFF 갱신 + Issue 코멘트 + PR (merge는 사용자 지시 대기)
```

구현 워커는 git을 실행하지 않는다 — 커밋은 conductor가 수행(프로세스 개정). `scripts/verify.sh`는 현재 main에 부재(본 세션 확인) → 동등 명령 4종(`validate_scaffold.py`, `check_oq_updates.py`, `check_doc_links.py`, `pytest scripts/tests/ -q`) 또는 conductor가 스크립트 공급 **[추론]**.

| ID | 내용 | 파일 |
|---|---|---|
| T-1 | 검사기 본체: 질의 레지스트리(P-3)·스냅샷 모델(P-4)·completeness(P-6)·JSON/Markdown 렌더·capture 기록·CLI(P-8) | `scripts/db/mssql_inspect.py`(신규), `scripts/tests/test_db_mssql_inspect.py`(신규) |
| T-2 | canonical evidence path 절차 반영(P-13) | `.opencode/agents/db-analyzer.md`, `.opencode/skills/db-migration-analysis/SKILL.md` |
| T-3 | ignore 규칙 1행(P-7) | `.gitignore` |
| T-V | 호스트 검증(위) — 수정 없음 | — |
| T-R1 | 최종 독립 리뷰 1회 | 리뷰 보고 |
| T-F1 | 발견 일괄 수정 + conductor 재검증 | T-1..T-3 산출물 |
| T-H1 | 인계 | `HANDOFF.md`, GitHub |

T-1 테스트(finite fixture/fake — 실제 DB 불요; 코멘트 9항목 1:1): (1) fixture/golden JSON+Markdown 바이트 결정; (2) 레지스트리 전수 `classify_batch==read`+`INTO`·위험동사 비인용 토큰 부재(M-3); (3) 질의 기록 ⊆ 레지스트리, `--sql` 인자 부재, driver 심볼 부재(M-4); (4) `mssql-prod-ro` 외 프로필 거부; (5) `--expect-database` 불일치 → 종료 2 + inventory 질의 0회(fake 기록 증명, M-2); (6) definition NULL → `UNAVAILABLE`/`UNKNOWN`/sha 부재/카테고리 PARTIAL/`ABSENT` 부재(M-6); (7) msdb 실패 → `agent_jobs` BLOCKED(P-6 규칙)+경고+DB 객체 COMPLETE 유지(M-5); (8) job-step opt-in 4케이스(기본 NOT_REQUESTED·질의 미실행 포함); (9) JSON/Markdown 동일 스냅샷 모델·재실행 바이트 동일; (10) 기본 출력 경로가 `.gitignore`로 ignore됨(T-3 검증 겸용)+원문은 capture 파일에만; (11) 환경변수·파라미터 sentinel이 stdout/스냅샷/markdown/오류/capture 전 경로 부재(P-9); (12) capture context 완전성(설계 L139-147); (13) guard 차단(GuardBlockedError) → 비밀 아닌 reason+종료 2+partial capture 부재.

T-2 요구: `db-analyzer.md` Procedure에 (i) live evidence 가용 시 inspector 실행, (ii) 해석 전 completeness 확인, (iii) PARTIAL/BLOCKED 의존 결론은 불확실성 보존 반환, (iv) raw/자격 복사 금지 — 절차 문장 추가에 한정. `SKILL.md`에 동일 경로 + "소스 코드 SQL 문자열은 보강일 뿐 unavailable 정의 대체 아님"(설계 L266-268). 역할 선언·STOP payload·generated 블록 무변경. 기존 `test_agent_*`·`test_skill_execution_contract.py` green 유지(T-V에서 확인).

## 5. 설계 게이트 재오픈 트리거 (걸리면 중단·기록·사용자 판단 대기)

1. expected-target 값 공급 필요(M-1) — #20 소유 파일, 사용자 배포 사실만.
2. 한 프로필로 복수 DB 검사 요구 — profile당 identity 1쌍 모델(#20/#23) 변경 사안.
3. allowlist 커버리지 확장(설계 L139-186 밖) 또는 식별자 조립 필요(P-3).
4. PARTIAL/BLOCKED 경계 등 completeness 규칙 변경 요구(P-6).
5. 분류기 완화 압박 — allowlist 질의가 `read` 미인정 사례 발생(#20 트리거 계열, 우회 금지).
6. guard API 확장 필요(`open_readonly` 시그니처 등) — #20 설계 변경.
7. raw capture 위치 변경/durable evidence store 연계(설계 L130·L248).
8. `OMITTED_BY_POLICY` 생성 경로 필요(P-10).
9. #22 core와 shared-file(`.gitignore`/HANDOFF) 충돌 — merge 순서 질의.
10. agent/skill 변경이 persistence 경계·STOP payload 침범 요구(P-13).
11. #23 금지 입력(.env auto-load, raw 연결 문자열, 임의 env-var) 요구.

## 6. 사용자 확인 항목 (open questions — 임의 확정 금지)

1. **PARTIAL vs BLOCKED 경계 규칙 — 결정됨 (2026-10-07, 사용자 수용)**: 요청 범위에서 일부라도 회수 성공=PARTIAL, 원천 전체 접근 불가=BLOCKED. P-6는 더 이상 [추론]이 아니라 사용자 결정.
2. **expected-target `mssql-prod-ro` 값 공급 시점**(M-1): 라이브 검증 전 사용자가 `target_metadata.py` 값을 공급하는 시점·절차(#18 세션이 아닌 별도 승인 하 변경).
3. **live validation 환경**(비범위): DBA 승인 read-only 계정·msdb 가시성·`MSSQL_PROD_RO_CONN` 주입 확보 시점(설계 L94, Phase 1 조건).

## 7. 명시적 비범위

live MSSQL validation(Phase 1, DBA 승인 환경 — 설계 L273-291) / OQ-013 해소(경로만 제공, L269-271; OQ-013 OPEN 유지) / raw SQL 경로(L31·L99-103) / 응용 행 export(L68-75·L295) / T-SQL 파싱·번역, PG 설계, materialization, 스냅샷 diff, dependency graph, 서버 트리거 분석(L174-175·L295) / expected-target 값 주입·계정 프로비저닝(P-12).

## 8. PR/merge 권장

단일 PR(도구+테스트+`.gitignore`+문서 = 하나의 수직 슬라이스; 분리 시 "도구 존재+raw 경로 미보호" 혼합 계약 상태 — no-mixed-contract 선례). Track D 3번, #22 core와 병렬 가능(공유 파일 재확인 후). PR 개설 후 사용자 명시 merge 지시 대기, merge 직전 `git log <base>..HEAD` 재확인. **본 문서의 커밋은 구현 승인이 아니다 — 구현 착수 전 사용자 go-ahead 필요(rule 13, 게이트 4).**
