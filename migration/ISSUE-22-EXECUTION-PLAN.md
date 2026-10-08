# Issue #22 core 실행 계획 — DB 스냅샷 canonical 인코딩 + before/after delta (`scripts/db/db_snapshot_diff.py`)

작성일: 2026-10-08 / 기준 커밋: `fd6bb4d`(=origin/main, 워크트리 `hjung3113/issue22-core`, diff 0)
Canonical design: `docs/issue-22-db-snapshot-diff-contract.md`(370줄, PR #48). 본 계획은 설계를 재진술하지 않고 core 구현만 계획한다.
상위 계획: `migration/ISSUES-PLAN-DRAFT.md` D-C(L115-132) — "먼저 DB 비의존 core"(L121-128), "그 뒤 read-only `capture`와 `DbAssertionPort` adapter를 #20 guard에 연결"(L130), 마일스톤 M3 = `#22 core`, M4 = `#22 live adapter`(L172-173).
이슈: #22 본문(일부 stale — 게이트 2) + 코멘트 2건(#23 프로필 규약, PR #48 merge 보고의 9항목 구현 범위).
사실 표기: `(근거: 파일:줄)` / `(본 세션 실행 확인)`, 설계 미고정 판정은 **[추론]**.

## 1. 게이트 체크 (7항목 — ISSUES-PLAN-DRAFT L178+)

기본 상태(본 세션 실행 확인): 워크트리에서 `verify.sh` ALL PASS, `pytest scripts/tests/` **680 passed**, open PR 없음.
- **게이트 1 통과** — 설계 370줄 전문, 상위 계획 D-C, 이슈 코멘트 2건, 소비 모듈(`sql_classification.py` 공개 API `classify_batch` L139, `db_guard.open_readonly` L77, `migration/judge/ports.py`) 확인.
- **게이트 2 통과** — 본문 stale 미채택: CSV 스냅샷→JSON 전용(설계 L46), comparison semantics를 도구가 읽어 적용→도구는 raw 구조 delta만, 의미론은 adapter(설계 L45, L214-227), "커넥터 주입"→read-only capability만(설계 L44, L156), whole-state 비교→feature-scoped delta(설계 L43, L88).
- **게이트 3 통과** — core는 DB 비의존(상위 계획 L121). 재사용할 `classify_batch`는 순수 함수이고 driver-boundary 검사(`validate_scaffold.py:965-980`)가 금지하는 driver/connector import가 아님.
- **게이트 4 통과 (2026-10-08)** — 사용자가 계획 검토 후 "진행해"로 구현 착수와 §6-1·§6-2 권장안을 함께 승인.
- **게이트 5 통과** — 범위 = 상위 계획 L123-128 core 6항목 중 §6-1을 제외한 5항목 + plan 파일 정적 검증. capture/adapter/문서 연결은 범위 밖(§7).
- **게이트 6 통과** — §5 트리거 + rule 13.
- **게이트 7 통과** — open PR 없음. 공유 파일은 `.gitignore` 1행뿐. 다른 진행 브랜치 없음.

## 2. core 경계 판정 (상위 계획 L123-128 × 설계)

- **C-1 [포함]** canonical typed JSON / digest — 설계 L169-194.
- **C-2 [포함]** before/after 스냅샷 pairing 검증 — 설계 L196-206.
- **C-3 [포함]** `delta`(added/removed/updated/unchanged_count) — 설계 L90-99.
- **C-4 [포함]** raw-value-free `render` — 설계 L144, L293.
- **C-5 [포함]** stable key / hard `max_rows` / 결정론 정렬 검증 — 설계 L140-143, L194.
- **C-6 [보류 제안 → §6-1]** staged synthetic-mutation negative control. 설계상 이 컨트롤은 "실제 판정에 쓰는 **같은 adapter/비교 configuration**"이 known-wrong 쌍을 거부해야 성립(설계 L251-252, L342). core에는 그 adapter(의미론 비교기)가 없으므로, core에서 만들 수 있는 것은 "변형기 + 구조 delta가 달라짐" 테스트뿐이고 이는 아무 detector도 검증하지 않는다. → adapter와 같은 PR(live adapter 단계)로 옮기는 것을 권장.
- **C-7 [포함, 상위 계획 목록 밖이나 C-1·C-5의 입력]** `db-comparison-plan.json` 로드·정적 검증(설계 L101-146). 스냅샷 빌더가 subject 정의(columns/key_columns/max_rows/query digest)를 소비하므로 core에 필요.
- **C-8 [제외]** `capture` 서브커맨드·DB 접근 — 상위 계획 L130이 다음 단계로 명시. core에는 `capture`가 나중에 호출할 순수 빌더 함수만 둔다.

## 3. 파생 판정 P-1..P-12 (신규 lock-in 아님 — 근거 인용)

- **P-1 배치**: 단일 `scripts/db/db_snapshot_diff.py` + 단일 테스트 `scripts/tests/test_db_snapshot_diff.py`. 근거: 이슈 코멘트 1항, 설계 L300-303, #18 선례. 표준 라이브러리 + `scripts.db.sql_classification`만 import(설계 L146).
- **P-2 plan 정적 검증**: 엄격 스키마(알 수 없는 키 거부). `version==1`, `feature_id` 비어있지 않음, `subject_id` 유일, `mode ∈ {delta, state}`, `columns` 비어있지 않고 중복 없음, `key_columns ⊆ columns`, `max_rows` 양의 정수, `comparison_rule_ref` 비어있지 않은 문자열(추적용일 뿐 해석하지 않음, 설계 L224), `legacy_query`/`target_query` 둘 다 필수. 근거: 설계 L113-145. **[추론]** 엄격 스키마와 필드별 규칙.
- **P-3 질의 정적 검사**: 각 질의는 `classify_batch(...)` 결과가 단일 `read`여야 함(EXEC/DML/DDL/다중문/`SELECT INTO` 거부, 설계 L162). `SELECT *`/`t.*` 거부는 토큰 수준(`*` 앞 토큰이 `SELECT`/`DISTINCT`/`,`/`.`이면 거부, `COUNT(*)`·곱셈은 허용) **[추론]**. 최종 보증은 빌더의 결과 컬럼 정확 일치(P-5)이며 정적 검사는 조기 차단용. `?` 개수 == `len(required_parameters)` 검사 **[추론]**(위치 바인딩 순서 = `required_parameters` 순서).
- **P-4 빈 키 규칙**: 설계 L140의 "one row expected 선언"을 새 필드 대신 `key_columns == []` ⇒ `max_rows == 1` 강제로 표현 **[추론]** — v1 스키마(설계 L113-133)에 필드를 추가하지 않는 최소안. → §6-2 확인.
- **P-5 스냅샷 빌더(순수 함수)**: 입력 = 검증된 subject, side(`legacy|target`), moment(`before|after`), 메타(feature/run/fixture ref/engine/비밀 아닌 profile identity/스키마 리비전/capture 시각), 파라미터 값, 결과 컬럼 이름, 행. 결과 컬럼 ≠ 선언 `columns`(순서 포함) → 오류. 행 > `max_rows` → BLOCKED, 산출물 없음(설계 L143). 키 중복·키 값 NULL → BLOCKED(설계 L47; NULL 키 거부는 **[추론]**). 원시 파라미터 값은 저장하지 않고 digest와 이름 집합만(설계 L183-184).
- **P-6 canonical 값 인코딩**: 태그 값 `{"t": <type>, "v": <str|bool|null>}`, 타입 = `null/bool/int/decimal/float/text/date/time/datetime/binary`(설계 L192 최소 목록). `bool`은 `int`보다 먼저 판정. decimal = `str(Decimal)`(scale 보존, float 경유 금지, NaN/Inf 거부). float = `repr`, 비유한값 거부. datetime은 ISO-8601, tz-aware는 오프셋 포함·naive는 미포함(구별 유지). binary = 소문자 hex. 그 밖의 타입 → 오류(설계 L192 "unsupported fail"). **[추론]** 태그 이름·문자열 표현.
- **P-7 digest·봉투**: 파일 = `{"content_sha256": <hex>, "payload": {...}}`. digest = `sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))`, payload에 digest 필드 없음(설계 L52, L190). 로드 시 재계산해 불일치하면 거부 **[추론]**. 스냅샷·delta 모두 동일 규칙. payload에 `format`(`db-snapshot`|`db-delta`)과 `format_version: 1`.
- **P-8 정렬**: 행은 키 값의 canonical JSON 바이트 순으로 저장(설계 L194 "encoding detail only").
- **P-9 pairing·delta**: 설계 L198-206의 7개 불변식 전부 검사. 하나라도 어긋나면 BLOCKED, delta 산출물 없음(설계 L210). 추가로 before.moment==`before`, after.moment==`after`. delta payload = 양쪽 스냅샷 digest + 공통 메타 + `added`/`removed`(키+행) + `updated`(키, `changed_columns`, 전후 전체 행 — 설계 L99) + `unchanged_count`. `mode == state`인 subject의 delta도 계산은 허용(구조 계산일 뿐), 의미 판정은 adapter 몫.
- **P-10 render**: 스냅샷/delta 파일 1개 이상 → Markdown 표. 열 = 종류, subject, side, moment, digest, 행 수 또는 added/removed/updated/unchanged 수, 변경 컬럼 **이름**. 키 값을 포함한 모든 행 값은 출력하지 않음(설계 L144, L293). verification 템플릿의 Semantic result 열은 adapter 몫이라 채우지 않음.
- **P-11 CLI·종료 코드**: argparse, 서브커맨드 `delta --before P --after P [--output P]`, `render ARTIFACT... [--output P]`. 0 정상 / 1 사용법·입력 파일 형식 오류 / 2 BLOCKED(pairing 불일치·digest 불일치). stdout은 짧은 요약(digest, 개수)만, 행 값 없음. delta 기본 출력 = `.artifacts/db/<feature-id>/<run-id>/<subject>.<side>.delta.json`(설계 L261) **[추론]** 파일명.
- **P-12 `.gitignore`**: `.artifacts/` 1행(설계 L264, 이슈 코멘트 5항).

## 4. 태스크 (DAG)

```text
T-0 (완료: 본 문서) → [사용자 go-ahead] → T-1 ∥ T-2 → T-V 호스트 검증 → T-R1 최종 독립 리뷰 1회
    → T-F1 일괄 수정 1라운드(conductor 재검증) → T-H1 HANDOFF + PR (merge는 사용자 지시)
```

| ID | 내용 | 파일 |
|---|---|---|
| T-1 | plan 검증(P-2..P-4) · 빌더(P-5) · 인코딩/digest(P-6..P-8) · pairing/delta(P-9) · render(P-10) · CLI(P-11) | `scripts/db/db_snapshot_diff.py`(신규), `scripts/tests/test_db_snapshot_diff.py`(신규) |
| T-2 | ignore 1행(P-12) | `.gitignore` |
| T-R1 | codex gpt-6.1-sol xhigh(구현자 omp GLM과 다른 모델) | 리뷰 보고 |

T-1 테스트(설계 L315-332 중 core 해당분 1:1, 실제 DB 없음): (1) 동일 payload → 동일 canonical 바이트·digest, 행 입력 순서 무관; (2) digest가 `content_sha256` 필드를 제외하고 계산됨 + 변조 파일 로드 거부; (3) NULL vs 빈 문자열 구별; (4) decimal `Decimal("12.30")` 보존·float 미경유, NaN 거부; (5) binary/date/time/datetime(naive·aware) 인코딩, 미지원 타입 거부; (6) 중복 키 BLOCKED; (7) 다중 행 subject의 빈 키 거부 + 빈 키는 `max_rows==1`일 때만(P-4); (8) 결과 컬럼 불일치(추가·누락·순서) 거부, plan의 `SELECT *`/`t.*` 거부·`COUNT(*)` 허용; (9) `max_rows` 초과 BLOCKED + 산출물 파일 없음; (10) added/removed/updated/unchanged 계산, updated에 전후 행·변경 컬럼; (11) pairing 불변식별 불일치 각각 BLOCKED(run, query digest, parameter digest, columns, keys, fixture, side, moment 역전) — 파라미터화; (12) plan 질의 중 EXEC/DML/DDL/다중문/`SELECT INTO` 거부(`classify_batch` 경유); (13) render 출력·stdout·오류 메시지에 행 값·키 값·파라미터 값 sentinel 부재; (14) CLI 종료 코드 0/1/2와 BLOCKED 시 출력 파일 미생성; (15) 기본 출력 경로가 `git check-ignore`로 ignore됨.

설계 L330("read-only-profile failure before query execution")과 L332(adapter negative control)는 capture/adapter 테스트라 core 범위 밖(§7).

## 5. 설계 게이트 재오픈 트리거 (걸리면 중단·기록·사용자 판단)

1. plan v1 스키마에 필드 추가 필요(P-4 대안 포함).
2. 태그 인코딩으로 표현 못 하는 타입을 지원해야 함(P-6 — 설계 L192 "explicit canonical representation" 필요).
3. 도구 안에 정규화/허용오차/순서 규칙을 넣으라는 압박(설계 L223 위반).
4. 분류기 완화 압박 — 정당한 snapshot 질의가 `read`로 분류되지 않음(#20 소유).
5. DB 접근·`capture`·adapter 코드가 core에 필요해짐(C-8, 상위 계획 L130).
6. raw 산출물 위치 변경 또는 durable store 연계(설계 L278).
7. render에 값 표시 요구(설계 L144 "explicit design change").
8. pairing 불변식 완화 요구(best-effort 매칭 — 설계 L210 금지).

## 6. 사용자 확인 항목 (임의 확정 금지)

1. **C-6 negative control 시점 — 결정됨 (2026-10-08)**: live adapter 단계로 이동. core에는 변형기를 넣지 않는다.
2. **P-4 빈 키 선언 — 결정됨 (2026-10-08)**: 새 필드 없이 `key_columns == []` ⇒ `max_rows == 1`. P-4는 더 이상 [추론]이 아니라 사용자 결정.
3. (참고, 이번 결정 불요) live adapter 단계 선행 사실: 커넥터가 파라미터를 그대로 넘겨 paramstyle이 엔진별로 다름(`connectors/mssql.py:111-115`, `postgresql.py`), `fetch_all`이 결과 컬럼 이름을 돌려주는지 미확인, 부작용 캡처 대상 테스트 DB를 `open_readonly`로 열 프로필 결정(#20/#23) — 모두 adapter 계획에서 다룬다.

## 7. 명시적 비범위

`capture` 서브커맨드·DB 접근·guard 연결(상위 계획 L130) / concrete `DbAssertionPort` adapter·behavior-contract 의미론 적용(설계 L214-240) / negative control(§6-1 결정: live adapter 단계) / `parity-verification` SKILL·verifier 절차·`docs/templates/verification.md` 연결(이슈 코멘트 7항 — 동작하는 capture 없이 절차를 쓰면 실행 불가능한 지시가 됨 **[추론]**) / validator에 plan 파일 검사 추가(현존 plan 파일 0개) / 설계 비목표 전부(설계 L345-356).

## 8. PR/merge 권장

단일 PR(도구+테스트+`.gitignore`). PR 개설 후 사용자 명시 merge 지시 대기. #22 이슈는 live adapter가 남으므로 core merge 후에도 open 유지하고 코멘트로 진행 상황 기록. **본 문서의 커밋은 구현 승인이 아니다 — 구현 착수 전 사용자 go-ahead 필요(rule 13, 게이트 4).**
