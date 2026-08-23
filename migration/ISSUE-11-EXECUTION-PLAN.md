# Issue #11 실행 계획 — judge self-check hardening (mandatory negative control) 구현

작성일: 2026-08-24
기준 커밋: `fe937ec` (= `origin/main`, 본 워크트리 `hjung3113/issue11-plan` 분기점)
Canonical design: `docs/03-evidence-and-verification.md` (§"Judge self-check gate — mandatory
negative control", L114–149) + `migration/RULEBOOK.md` Agent workflow #7 (L96) +
`docs/templates/verification.md` — 세 문서 모두 이미 병합된 canonical 정책
상위 계획: `migration/ISSUES-PLAN-DRAFT.md` — P-R 레인 `(#7, #8) -> #6 -> #11`, Track P
merge 순서 9번(마지막). P-R 레인 노트(L72)와 Track D 교차 의존성 노트(L76) 참조
이슈 본문: GitHub Issue #11 "[A-9][Critical] parity-verification/verifier의 judge
자기검증이 'where practical'로 선택사항화됨" (본문 권고 일부 stale — 게이트 2 참조)

이 문서는 (1) ISSUES-PLAN-DRAFT "구현 시작 전 체크" 7항목을 현재 `main` 기준으로
재확인한 결과와 (2) #11 구현의 실행 계획(DAG)을 담는다. 이 문서 자체는 구현이
아니며, 구현 승인 절차를 대체하지 않는다. **이미 병합된 docs/03 / RULEBOOK:96 /
verification.md 템플릿의 정책 문구를 재설계하거나 재개방하지 않는다** — 남은
범위는 그 정책에 운영 파일 2개를 정렬하고 그 자체 불변식을 validator가 강제하는
것뿐이다.

---

## 1. 게이트 체크 결과 (7항목 전부 확인, 블로커 없음)

모든 확인은 문서 예시가 아니라 현재 `main`(=본 브랜치 HEAD `fe937ec`)의 실제 파일
기반이다. 이 시점의 기본 상태(본 세션 실행으로 확인): `python3
scripts/validate_scaffold.py` exit 0, `python3 -m pytest scripts/tests/ -q` —
373 passed, `check_doc_links.py` / `check_oq_updates.py` green, open PR 없음.

### 게이트 1 — canonical design 문서를 읽었는가 → 통과

세 canonical 문서를 전문 읽고 현재 `main`과 대조했다.

- `docs/03-evidence-and-verification.md` L114–149: mandatory negative-control
  self-check 게이트. 핵심 정책 — effective configuration 정의(필수 소스 집합, 구체
  adapter/수동 절차, 비교/정규화 규칙, fixture/schema/environment 버전, judge 구현
  revision), negative-control 규칙 1–6(그중 규칙 6이 L135 "**There is no `where
  practical` waiver.**" — 불능은 예외 면제가 아니라 self-check `BLOCKED`), self-check
  상태 3치(PASS/FAIL/BLOCKED), L143 커플링(self-check FAIL/BLOCKED → 전체 결과
  BLOCKED, nominal parity 결과와 무관), L145 fingerprint 동일 + 증거 인용 없이는
  재사용 금지, L147 S-011 synthetic self-test의 한계(변경된 adapter/소스 집합/규칙/
  환경을 승인하지 않음), L149 "모든 verification artifact는 template으로 self-check
  상태·effective configuration/fingerprint·control injection·expected detectors·
  actual detector results·evidence/reuse reference·blocker를 기록해야 한다".
- `migration/RULEBOOK.md` L96 (Agent workflow #7): 신뢰 verdict 금지 + synthetic
  self-test 비승인 + failed/unavailable self-check → BLOCKED.
- `docs/templates/verification.md`: L5 헤더 필드 `Judge self-check: PASS | FAIL |
  BLOCKED` (3치 — PARTIAL 없음), L7 "`Result` must be `BLOCKED` unless `Judge
  self-check` is `PASS`.", L9–22 `## Judge self-check` 섹션(필드 6종 + 고정
  8컬럼 JC-### control 표 + "Reuse is valid only when the … fingerprint is
  identical …").
- 부가 정합: docs/03 L99(DB 소스 negative control은 staged synthetic snapshot/delta
  mutation — 공유 DB 변조 금지, #22 설계와 정렬), L190(수동 증거도 self-check 면제
  없음 — 안전하게 challenge 불가 시 BLOCKED).

설계가 전제하는 "이미 병합된 canonical" 상태가 실제 성립함을 확인했다. 반대로
운영 파일 2개는 아직 정책에 정렬되지 않았다(게이트 3의 현황 표 참조).

### 게이트 2 — 이슈 본문의 stale recommendation을 그대로 구현하지 않는가 → 통과

이슈 #11 본문 대비 확정된 차이 (merged canonical design이 우선, 계획 원칙 1):

| 이슈 본문 권고 | 현재 설계의 판정 | 구현 시 지침 |
|---|---|---|
| "where practical" 제거 + 번호 매긴 필수 단계로 승격("0단계" 안내 문구, 생략 시 PASS 보고 금지) | 방향은 설계가 이미 채택·병함(docs/03 §"Judge self-check gate" + template L5/L7). 단 "0단계" 번호 체계와 세부 문구는 설계가 이미 다른 형태(스킬 규칙 7 / verifier 절차 3단계 슬롯 + template 섹션)로 소유 | 본문 문구를 복사하지 않고 docs/03/RULEBOOK:96/template를 근거로 기존 슬롯에서 재작성(§3 P-1/P-2) |
| "practical하지 않은 경우"의 구체적 예외 조건(화이트리스트) 명시 | 설계가 명시적으로 거부: docs/03:135 규칙 6 — 예외 나열이 아니라 안전한 고립 경로 확인 후에도 불능이면 self-check `BLOCKED`(이는 "종료 조건 검증 불능"이지 면제가 아님). 이슈 본문 유의점의 "화이트리스트 + BLOCKED 유지"보다 설계가 더 강함(화이트리스트 자체가 없음) | 예외 조건 열거/화이트리스트 금지. 불능 → BLOCKED로 통일 |
| `docs/templates/verification-report.md`에 "Judge self-check" 필드 추가 | 경로 stale — canonical 템플릿은 `docs/templates/verification.md`이고 필드·섹션·JC-### control 표가 이미 병합됨(`migration/features/synthetic-demo/verification.md`가 이미 이 형식으로 작성됨) | 템플릿 무변경(Non-goal). 대신 validator가 템플릿 자체 불변식을 강제(본 계획 T-2) |

본문의 인용 줄번호(`SKILL.md:25`, `verifier.md:15`)는 현재 각각 93/42로 드리프트.
본문의 문제 진단(강제 안전장치가 "where practical" 재량으로 약화)은 유효하며
정확히 잔여 범위와 일치한다. stale 본문을 그대로 따르는 항목은 없다.

### 게이트 3 — 선행 contract가 실제 main에 구현되어 있는가 → 통과

P-R 레인상 #11의 선행(#7, #8, #6)과 validator 기반(#1/#2)이 모두 병합됨. 현재
`main`의 실제 파일에서 확인:

| 선행 요소 | 위치(`fe937ec` 기준) | 확인 내용 |
|---|---|---|
| A-2 `validate_verification()` | `scripts/validate_scaffold.py` L1155–1188 | 기능 현황: duplicate-key 전체 헤더 검사, `Result` enum(`VERIFICATION_RESULTS` L858), Grade 컬럼 enum. **self-check 관련 검사 전무** — 아무것도 `Judge self-check` 필드·섹션·커플링을 강제하지 않음(본 계획 T-2 대상) |
| 파싱 인프라 | `_split_sections` L957, `_parse_kv` L985(`KV_FIELD_RE` L865 `^-\s+([^:]+):\s*(.*)$` — 섹션 본문의 `- Key: value` 필드에도 적용 가능), `_parse_tables` L922, `_cell` L947, `_unique_fields` L995, `_err` L1009 | T-2가 재사용할 헬퍼. 고정 컬럼 정확 일치 검사의 직접 선례: #9의 `GRADE_HISTORY_COLUMNS` L839 + `_validate_grade_history()` L1191 |
| 발견 범위 | `validate_feature_schemas()` L1546–1548 | verification 인스턴스 = feature 디렉터리 singleton `verification.md` 한정. `docs/templates/`은 스캔 대상 아님 → 템플릿 자체는 새 검사로 깨지지 않음 |
| #6 skill execution contract | `validate_skill_execution_contract()` L348; `parity-verification/SKILL.md` 실측 5섹션(Inputs/Outputs/Procedure/Branches/Done means) + `[Input]`/`[Output]` 마커 보유 | T-1 재작성이 이 구조를 green으로 유지해야 함 |
| #7 routing | `validate_skill_routing_contract()` L290; SKILL.md `## Primary artifact boundary`/`## Skill tie-break` 존재, verifier.md `Invoke when`/`Do not invoke for`/`Primary output ownership` 존재 | 재작성이 routing 섹션 불변 유지 |
| #13 STOP | verifier.md `## Stop handling` 12필드 payload + managed STOP block + Escalation 위임 존재 | verifier.md 재작성이 해당 영역 무변경 |
| 잔여 hedge 실측 | `SKILL.md` L93(규칙 7 "…where practical;"), `verifier.md` L42(절차 3단계 "Validate the judge where practical …") | 전 repo grep: 운영 파일 내 "where practical"은 정확히 이 2곳. `docs/03:135` 소속 문구(규칙 6 인용)와 `docs/00:50`(characterization 테스트 권고 — #11 비소관)는 정상 존치 |

인스턴스 현황: feature 디렉터리의 verification.md는 `synthetic-demo` 1개뿐이며,
헤더(`Result: PASS` L8, `Judge self-check: PASS` L10)·`## Judge self-check` 섹션
(필드 6종 L17–28, JC-001 PASS 행 L30–32 포함)을 이미 템플릿 정합으로 기록 →
T-2 신규 검사가 오늘날 저장소를 깨뜨리지 않는다(안 깨지면 §5 트리거 2 상황).
단 `test_validate_schema.py`의 `VALID_VERIFICATION` fixture(L38–48)는 self-check
필드·섹션이 없어 T-2에서 정합 갱신 필요(§3 P-8).

### 게이트 4 — 사용자의 명시적 구현 승인 → 조건부 통과 (이번 세션은 구현 없음)

- `AGENTS.md` rule 13 (design gate) 유효.
- HANDOFF.md 최신 항목(2026-08-23): "**Rule-13 Track P/D authorization remains in
  effect and has not been revoked.**" + "Before starting #11, redo the 7-item gate
  against current `main` …" — 본 세션 지시가 바로 그 게이트 재실행 + 실행 계획
  작성이다.
- ISSUES-PLAN-DRAFT 원칙: "이 계획 문서 또는 PR의 merge만으로 승인됐다고 간주하지
  않는다." **본 실행 계획 문서 자체가 구현 승인이 아니다.** 본 세션 지시는 "게이트
  체크 + 실행 계획 문서 + 커밋"으로 한정되어 있으므로 **본 세션에서는 구현 코드를
  작성하지 않는다.** 구현 세션은 standing authorization과 이 게이트 결과가
  green임을 재인용한 뒤 착수한다.
- 게이트 결과에 블로커가 없으므로 별도 승인 질의 항목은 없다.

### 게이트 5 — 구현 범위가 acceptance criteria를 넘지 않는가 → 통과

범위 상한 = 병합된 canonical 정책이 운영·기계 계층에 요구하는 것 + 본 세션 지시가
명시한 validator 강화. 구체적으로:

- 변경: `.opencode/skills/parity-verification/SKILL.md`(규칙 7 재작성 + 절차 4단계
  최소 보강), `.opencode/agents/verifier.md`(절차 3단계 재작성),
  `scripts/validate_scaffold.py`(`validate_verification()` 내부 확장),
  `scripts/tests/test_validate_schema.py`(fixture 정합 + 신규 검증 테스트), 신규
  `scripts/tests/test_judge_self_check_contract.py`(운영 파일 내용계약).
- 비변경(Non-goals): **`docs/03-evidence-and-verification.md`,
  `migration/RULEBOOK.md`, `docs/templates/verification.md` 정책 문구 전부**(이미
  canonical — 재개방 금지가 이 이슈의 전제), `migration/judge/` 코드(S-001/S-011
  소유), fingerprint 형식 정의(canonical 문서가 규정 안 함 — 발명 금지, §3 P-7),
  다른 7개 스킬/다른 에이전트 파일, `.opencode/commands/*`, DB 어댑터/가드(Track
  D), CI 신규 job, `migration/features/synthetic-demo/verification.md` 본문(이미
  정합 — 정규화 대상 아님), 이슈 본문의 화이트리스트/`verification-report.md`
  방향(stale — 게이트 2).

### 게이트 6 — 새 lock-in 결정 시 design gate 재오픈 근거 → 통과

재오픈 메커니즘이 3중으로 존재: ISSUES-PLAN-DRAFT 계획 원칙 2, AGENTS.md rule 13,
본 계획 §5의 명시적 트리거. #11은 특히 "canonical 정책 재개방 금지"가 범위의
전제이므로 §5 트리거를 구현 세션에 전달한다.

### 게이트 7 — shared file merge 순서 → 통과

- `gh pr list` open PR 없음(본 세션 확인). 본 브랜치 = `origin/main`(`fe937ec`)
  분기 직후, 커밋 없음.
- Track P는 #11이 마지막(HANDOFF: "After #11, Track P is complete"). #9 세션 파일
  (evidence-grading 스킬, evidence-record 템플릿, grade transition 스크립트)과 #11
  파일은 무교집합(HANDOFF 명시). Track D(#18/#20/#22/#23)는 `scripts/db/` 중심으로
  무관.
- `scripts/validate_scaffold.py` 충돌 패턴: T-2는 기존 `validate_verification()`
  내부를 확장(#9의 `validate_evidence_record()` 확장과 동일 패턴). 해당 함수를
  수정하는 다른 진행 중 작업이 없으므로(위 확인) 순차 단일 PR이면 충돌 없음.
- #6 세션 F1/F2 교훈(batch 재작성이 조건절/참조를 조용히 누락)이 T-1(스킬/에이전트
  파일 재작성)에 직접 적용된다 — §4 T-1에 보존 체크리스트로 명시. #6 세션의 F5
  사례("where practical"이 재작성 중 신규 위치로 유입)가 정확히 이 이슈의 역방향
  회귀(T-1 후 운영 파일에 재유입 금지 + T-2 검사와 별개로 내용계약 테스트가 감시)이다.

---

## 2. 현재 구현 기준선 (구현 세션이 기대해야 하는 출발 상태)

### `.opencode/skills/parity-verification/SKILL.md` (97줄, #6/#7 구조)

섹션: `## Primary artifact boundary`(#7) → `## Skill tie-break`(#7) → `## Inputs` →
`## Outputs` → `## Procedure`(7단계, 마커 포함) → `## Branches` → `## Done means` →
`## Judge inputs and rules`(judge 입력 후보 + 규칙 1–11). 잔여 hedge는 규칙 7
(L93). 절차 4단계(L53 "validate the judge with a controlled mismatch")는 무-hedge
지만 docs/03 게이트 절·template 기록 의무를 가리키지 않는다. 규칙 4–5(PostgreSQL
guarded target — #22/#20 인접 보존 대상)와 규칙 1–3(비교 규칙 사전 확정/BLOCKED)
및 8–11은 무변경 보존 대상. `validate_skill_execution_contract()` /
`validate_skill_routing_contract()` / `validate_skills()`가 구조를 강제 — T-1은
항상 green 유지.

### `.opencode/agents/verifier.md` (94줄, #7/#13 구조)

`Invoke when`/`Do not invoke for`/`Primary output ownership`/`Artifact contract`/
`Procedure`(6단계)/`Stop handling`(12필드 payload)/`Stop conditions`(managed)/
`Escalation`(payload 위임). 잔여 hedge는 절차 3단계(L42)뿐. 절차 1·4단계의 BLOCKED
조건들, 5단계 verdict 배정 규칙은 무변경 보존 대상.

### `scripts/validate_scaffold.py` (2382줄)

`validate_verification()`(L1155–1188) 현재: duplicate-key(헤더 전체), `Result`
enum, 테이블 Grade 컬럼 enum. `_split_sections`가 섹션별 라인을 반환하나
`validate_verification`는 현재 버림(`header, sections = _split_sections(lines)` 중
`sections` 미사용 — `sections`에서 title `"judge self-check"`(소문자화됨) 검색으로
확장). 고정 컬럼 검사·enum·행 불변식의 완성된 선례: `_validate_grade_history()`
(L1191–1375). 발견 경로/호출점(L1546–1548) 불변.

### 테스트 기반

`scripts/tests/test_validate_schema.py`(1000줄): `VALID_VERIFICATION` fixture
(L38–48) — `Judge self-check` 헤더·섹션 없음(T-2에서 갱신). verification 영역
기존 테스트(L709–755): Result 도메인/거부/빈 값 허용/Grade 셀/duplicate — 전부
`add_feature(verification_text=…replace(…))` 패턴이라 fixture 갱신 후에도 유지.
`test_skill_execution_contract.py`에는 parity-verification 구조 테스트 존재,
내용(규칙 문구) 테스트는 없음.

### 인스턴스/CI 현황

- `migration/features/synthetic-demo/verification.md`(100줄): 이미 정합(게이트 3).
  값의 줄바꿈 연속(`- Result: PASS` + 들여쓰기 연속행, L8–9)은 `KV_FIELD_RE`가
  첫 행만 매치하므로 문제없음.
- CI `repo-guards`: validator + doc links + OQ. pytest는 로컬/리뷰 회귀용(#9와 동일).
- 기준선(2026-08-24 실측): validator exit 0, pytest 373 passed, doc links/OQ green.

---

## 3. 파생 판정 사항 (신규 lock-in 아님 — 근거 명시)

구현 중 아래 판정은 임의 결정이 아니라 병합된 정책에서 유도된다. 구현자/리뷰어가
유도 근거에 동의하지 않으면 그때만 design gate를 재오픈한다.

- **P-1. SKILL.md는 기존 슬롯 재작성 — 규칙 7 same-slot 교체 + 절차 4단계 최소
  보강, 신규 섹션 없음.** 근거: #6 계약이 5섹션 구조를 고정하고 validator가 강제;
  `## Judge inputs and rules`의 11개 규칙 리스트가 judge 규칙의 정위치. 규칙 7의
  교체 문구는 docs/03 §"Judge self-check gate"(L114–149)와 RULEBOOK:96에서 유도:
  (a) negative-control self-check는 신뢰 verdict의 필수 조건, (b) 안전한 고립
  경로(경계) 확인 후에도 불능이면 self-check `BLOCKED` — `where practical` 면제
  없음, (c) self-check FAIL/BLOCKED → 전체 결과 BLOCKED(nominal parity와 무관),
  (d) template에 따라 상태·effective configuration/fingerprint·control injection·
  expected/actual detector results·evidence/reuse reference 기록, (e) 재사용은
  fingerprint 동일 + 인용된 증거일 때만. 절차 4단계는 docs/03 해당 절 참조 +
  template 기록 언급만 추가(단계 수·`[Input]` 마커 불변). `## Branches`의
  "unavailable source → PARTIAL" 조건문은 self-check 게이트와 다른 질문(소스 가용성
  vs 종료 조건 검증)이므로 **무변경**(F1류 조건절 손실 방지).
- **P-2. verifier.md도 기존 슬롯 재작성 — 절차 3단계 same-slot 교체.** P-1과 동일
  근거로 docs/03/RULEBOOK:96에서 유동, `**[Input]**` 마커와 6단계 구조 불변.
  현재 문구의 옳은 부분("if the judge cannot distinguish a mismatch, mark …
  `BLOCKED`")은 보존하되, "where practical" 재량 제거 + 검증자 관점 의무(선언된
  detector 전부 거부 증명, material mutation, 재사용 규칙, 기록 의무)를 망라.
- **P-3. validator 확장은 `validate_verification()` 내부 확장이지 sibling 최상위
  함수가 아니다.** 근거: #9 P-1과 동일 — 동일 인스턴스 발견 경로(L1546–1548),
  동일 호출점, `_split_sections`/`_parse_kv`/`_parse_tables`/`_unique_fields` 재사용.
  sibling은 발견·헤더 파싱을 중복한다. 신규 상수(`JUDGE_SELF_CHECK_RESULTS`,
  `SELF_CHECK_MODES`, control 표 고정 컬럼 튜플)는 `VERIFICATION_RESULTS`(L858)
  인근에 추가(#9 `GRADE_HISTORY_COLUMNS` 선례).
- **P-4. self-check 기록 필드는 무조건 존재 요구 — A-2의 validate-if-present 관례를
  정확히 이 필드들에 한해 상회.** 근거: docs/03:149 "Every verification artifact
  must use `docs/templates/verification.md` to record self-check status, effective
  configuration/fingerprint, control injection, expected detectors, actual detector
  results, evidence/reuse reference, and any blocker" — 조건부가 아니다. `Date`는
  요구하지 않는다(설계의 열거 밖 — 과경화 금지, #6 리뷰 F10 반성).
- **P-5. 커플링 의미: `Result` ∈ {PASS, FAIL, PARTIAL} ⇒ `Judge self-check` ==
  PASS.** 근거: template L7 + docs/03:143(self-check FAIL/BLOCKED → 전체 BLOCKED).
  역방향(self-check PASS + Result FAIL/PARTIAL)은 합법(검증 통과 + 실제 불일치).
  빈 `Result`는 기존 관례(신뢰 주장 부재 → 위반 아님)를 유지한다. 누락/빈
  self-check 필드는 커플링 판정에서 not-PASS로 취급(fail-closed).
- **P-6. control 표 검사 수위: 고정 8컬럼 정확 일치 + Outcome enum + mode=executed
  (또는 mode 필누락/무효)일 때 ≥1 행 + 헤더 PASS ⇒ 전 행 PASS.** 근거: template
  L18–20 고정 컬럼 + docs/03:139(PASS = "required controls were executed
  successfully")·131(detector 선언 후 전부 거부 증명)·133(no-op 가드 — Baseline/
  Known-wrong mutation 컬럼 존재 자체가 기록 의무). mode=reused일 때 행 요구는
  면제(재사용은 인용된 이전 증거가 그 역할 — template L22). 역방향(헤더 FAIL/BLOCKED
  + 전 행 PASS)은 canonical 문서가 못 박지 않으므로 기계화하지 않고 review 영역으로
  남긴다(#9 P-5와 동일 원칙). mode 필드 누락 시 fail-closed로 executed 요구를
  적용한다.
- **P-7. fingerprint 형식 검사 발명 금지 — 비어있지 않은 존재만 검사. mode=reused ⇒
  `Reused self-check evidence ref` 비어있지 않고 `N/A` 아님.** 근거: 어느
  canonical 문서도 fingerprint 인코딩을 규정하지 않음(docs/03:145는 "identical
  effective-configuration fingerprint" 동일성만 요구 — 형식은 미래 설계). 역방향
  (mode=executed + N/A 아닌 ref 기입)은 template이 금지하지 않고 안전 이득이 없어
  플래그하지 않는다. 재사용-무-인용이 안전 측 위반 방향이다.
- **P-8. 테스트 배치와 파일 소유권.** validator 강화 테스트는
  `test_validate_schema.py`의 verification 영역에 두고 `VALID_VERIFICATION`
  fixture를 정합(judge self-check PASS 헤더 + 섹션 + JC-001 행 포함)하게 갱신 —
  기존 replace-기반 테스트는 유지된다. 두 운영 파일의 내용계약(hedge 부재, 필수
  언어/참조 존재, 구조 불변)은 신규 `test_judge_self_check_contract.py`에 둔다(#9가
  스킬 내용 검사를 기존 파일에 둔 선례의 대응물 — 여기선 스킬+에이전트 두 파일을
  한 계약으로 다룬다). 이 배치가 T-1/T-2의 파일 소유권을 완전 분리한다(§4).

---

## 4. 태스크 분해 (DAG)

원칙: T-1(운영 파일 정렬)과 T-2(validator 강화)는 파일이 완전 분리되어 병렬
가능하다. 물리적으로는 **단일 브랜치/단일 PR**로 출하한다(§7).

```text
T-0 (완료: 이 문서) 게이트 체크 + 실행 계획
     |
     v
[병렬 그룹 A]  T-1 ∥ T-2   (파일 완전 분리)
     |
     v
T-I1 통합 검증 (validator + 전수 pytest + doc links/OQ + synthetic-demo 무변경 확인)
     |
     v
T-R1 독립 adversarial review (구현자와 독립, AGENTS.md rule 10)
     |                              — #6/#9 세션의 2단계(PR 본문 → diff) 패턴 재사용
     v
T-H1 HANDOFF.md 갱신 + Issue #11 구현 코멘트 + PR 개설(merge는 사용자 명시 지시 대기)
```

### 태스크 목록

| ID | 설명 | 대상 파일 | 선행 | 병렬 그룹 |
|---|---|---|---|---|
| T-0 | 게이트 7항목 재확인 + 본 실행 계획 작성·커밋 | `migration/ISSUE-11-EXECUTION-PLAN.md` | — | — (본 세션, 완료) |
| T-1 | **운영 파일 정렬**: ① `parity-verification/SKILL.md` 규칙 7 same-slot 재작성(P-1의 (a)–(e)) + 절차 4단계 docs/03 게이트 절·template 기록 참조 추가 ② `verifier.md` 절차 3단계 same-slot 재작성(P-2, `[Input]` 마커 유지) ③ 보존 체크리스트(#6 F1/F2/F5 교훈): 나머지 10개 judge 규칙 원문(특히 규칙 4–5 PG guard), 규칙 1–3/8–11, 5섹션 순서·마커·BLOCKED/PARTIAL 언급, #7 양 섹션, #13 STOP/Escalation, #8 읽기전용 persistence 위임, `docs/templates/verification.md`·docs/03 참조 존치, 모든 조건절 원문, **"where practical" 재유입 부재** ④ 신규 `scripts/tests/test_judge_self_check_contract.py`: 두 파일에 (i) "where practical" 부재 (ii) 필수 self-check 언어·BLOCKED 커플링·재사용 규칙·template/docs/03 참조 존재 (iii) 구조 불변(5섹션·마커·routing 섹션·STOP 위임) 문자열 존재 검사 | `.opencode/skills/parity-verification/SKILL.md`, `.opencode/agents/verifier.md`, `scripts/tests/test_judge_self_check_contract.py`(신규) | T-0 | A |
| T-2 | **validator 강화**: `validate_verification()` 내부 확장(P-3) — V1 `Judge self-check` 헤더 필드 필수 + enum PASS/FAIL/BLOCKED, V2 커플링(P-5), V3 `## Judge self-check` 섹션 정확히 1개, V4 섹션 필드 6종 필수·비음(Effective judge configuration / Configuration fingerprint / Self-check mode enum executed/reused / Reused self-check evidence ref / Safety-isolation note / Blocker) + mode=reused ⇒ ref ≠ N/A·비음(P-7), V5 control 표(P-6: 고정 8컬럼 정확 일치, mode=executed 또는 mode 결함 시 ≥1 행, Outcome 셀 enum), V6 헤더 PASS ⇒ 전 행 Outcome PASS. 신규 상수 L858 인근. 테스트: `test_validate_schema.py` — `VALID_VERIFICATION` 정합 갱신 + V1–V6 양성/음성 케이스(커플링 3치×self-check 3치 조합, reused 무인용, executed 무행, 컬럼 드리프트, 빈 Result 허용 유지, synthetic-demo 형태의 줄바꿈 연속 값) | `scripts/validate_scaffold.py`, `scripts/tests/test_validate_schema.py` | T-0 | A |
| T-I1 | 통합 검증: `python3 scripts/validate_scaffold.py` exit 0, `python3 -m pytest scripts/tests/ -q` 전수 green(373 + 신규), `check_doc_links.py`/`check_oq_updates.py` green, `git diff`로 synthetic-demo verification.md·canonical 3문서 무변경 확인, 구조 계약(스킬 실행/라우팅/에이전트/커맨드/STOP/durable state) green 유지 확인. 미달 시 수정 후 재실행 | (수정 대상 없음 — 검증 단계) | T-1, T-2 | — |
| T-R1 | 독립 adversarial review: §6 완료 기준 대조. 특히 (a) #6 F1/F2 패턴 — T-1 재작성 pre/post diff로 조건절·문서 참조 누락/변형 확인 (b) "where practical" 재유입 부재(운영 파일 전체, #6 F5 역방향) (c) validator 오탐 탐색 — 정당한 보고 형태(줄바꿈 연속 값, blockquote 노트, reused 모드 무행 표, 빈 Result, DB comparison 표의 PASS/FAIL/BLOCKED 셀 오탐) (d) 과경화 탐색 — canonical이 못 박지 않은 검사(P-6 역방향 등)를 몰래 넣지 않았는지 (e) Non-goals 준수·stale 권고 부활 없음. 발견 사항은 수정 후 re-verify | (리뷰 보고) | T-I1 | — |
| T-H1 | HANDOFF.md in-place 갱신(근거 SHA·테스트 수·남은 불확실성 포함), Issue #11에 구현 코멘트, PR 개설 + 리뷰 코멘트 게시 후 **사용자의 명시적 merge 지시 대기**(2026-08-22 워크플로 변경: Track P/D PR 자동 merge 금지). merge 후 소유자 리뷰 코멘트 추적(#61/#62/#65 선례) | `HANDOFF.md`, GitHub | T-R1 | — |

병렬성 요약: 그룹 A(T-1/T-2)는 파일 소유권이 완전히 분리되어 병렬 가능. 단일
세션 실행 시 순서 권장: T-2 → T-1(validator가 문서 형식을 먼저 확정하면 T-1의
문구가 기록 의무 전체를 참조하기 쉬움) → T-I1. 어느 쪽도 독립적으로 완료 가능하다.

---

## 5. 설계 게이트 재오픈 트리거 (구현 중 하나라도 걸리면 중단하고 기록)

1. **canonical 정책 문구 변경 필요성 발견.** T-1 문구 정렬이나 T-2 검사 설계 중
   `docs/03` / `RULEBOOK:96` / `docs/templates/verification.md`의 문구가 운영·기계
   계층과 양립 불가능하거나 누락/모순으로 판명되면, 그 문서를 임의 수정하지 않는다
   — 이 이슈의 전제("이미 canonical")가 깨진 것이므로 게이트를 재개방하고 사용자
   판단을 기다린다.
2. **정합 인스턴스 오탐.** T-2 신규 검사가 `synthetic-demo/verification.md`(또는
   템플릿 형식을 성실히 따른 보고서)를 깨뜨리면, 검사를 늦춰 우회하지 않고 그
   형태가 정책 문구로 정당한지 확인한다. 정당하면 §5 트리거 1로, 부정당하면(불성실
   기록) 그때만 인스턴스 정규화를 별도 승인으로 받는다.
3. **fingerprint 형식/동일성의 기계 검증 필요성 발생.** canonical 문서는 형식을
   규정하지 않으므로(P-7), 형식 검사·지문 산출 알고리즘을 만들어야 한다는 요구는
   신규 lock-in 설계 질문이다.
4. **self-check BLOCKED 커플링과 기존 Branches/PARTIAL 규칙의 충돌 발견.** P-1의
   판정(서로 다른 질문)이 무너지는 사례가 실제 나타나면 docs/03 수준의 모호성이므로
   재개방 대상이다.
5. **DB 소스 포함 configuration의 negative control 실측 필요성.** #11의 회귀
   테스트는 문서/validator 수준이며, DB 어댑터 포함 configuration의 실제 control은
   #22 live adapter 이후 별도 커버(ISSUES-PLAN-DRAFT L76). 그 조합을 지금 테스트해야
   한다는 요구가 생기면 Track D 의존성 질문으로 사용자에게 확인한다.
6. 그 외 "이슈 본문 권고를 그대로 구현해야 한다"는 유혹(게이트 2 — 화이트리스트,
   `verification-report.md` 템플릿 경로 모두 stale).

재오픈 시 취할 행동: 해당 design gate를 열고 `docs/05-open-questions.md` 또는
이슈 코멘트로 미결정 사항을 기록한 뒤 사용자 판단을 기다린다. 임의 결정 금지.

---

## 6. 검증/완료 기준

정책 → 구현 매핑:

| 요구(근거) | 담당 |
|---|---|
| "where practical" 부재 — SKILL.md·verifier.md 전체(docs/03:135 규칙 6의 역방향 회귀 방지, #6 F5 사례) | T-1 테스트 + T-R1 |
| 필수 negative-control self-check 언어·docs/03 게이트 절·RULEBOOK:96·template 참조 존재(docs/03:116/126/135, RULEBOOK:96) | T-1 테스트 |
| self-check FAIL/BLOCKED → 전체 BLOCKED 커플링 서술(docs/03:143, template L7) | T-1 문구 + T-2 V2 |
| 재사용 = fingerprint 동일 + 인용된 증거(docs/03:145, template L22) | T-1 문구 + T-2 V4(reused ⇒ ref) |
| 모든 verification artifact의 self-check 기록 의무 — 상태·configuration/fingerprint·control injection·expected/actual detectors·reuse ref·blocker(docs/03:149, template L5/L9–22) | T-2 V1/V3/V4/V5 |
| detector 선언·전부 거부 증명·materiality·no-op 가드·고립 경계 원칙(docs/03:128–134) | T-1 문구(운영 지시) — 기계화 대상 아님(실행 시점 사실) |
| synthetic/framework self-test가 변경된 adapter/소스/규칙/환경을 승인하지 않음(docs/03:147, RULEBOOK:96) | T-1 문구에 포함 |

추가 완료 기준:

- `python3 scripts/validate_scaffold.py` exit 0 — V1–V6가 기존 검사(A-1/A-2/
  durable state/STOP/skill/command/routing) 전부와 공존. 오늘날 인스턴스
  1개(synthetic-demo)가 무변경로 통과해야 함(안 되면 §5 트리거 2).
- `python3 -m pytest scripts/tests/ -q` 전수 통과(373 baseline + 신규).
- `check_doc_links.py`, `check_oq_updates.py` 통과.
- T-1 후 `validate_skill_execution_contract()` /
  `validate_skill_routing_contract()` / `validate_skills()` /
  `validate_agent_routing()` / `validate_agents_and_commands()` 전부 green 유지
  (구조 회귀 없음).
- canonical 3문서(docs/03, RULEBOOK, verification.md template)·`migration/judge/`·
  다른 스킬/에이전트/커맨드 파일·`docs/00:50` 무변경(Non-goals, T-I1 diff 확인).
- 독립 리뷰(T-R1)가 Non-goals 위반·선행 계약 훼손·stale 권고 부활·#6 F1/F2/F5
  패턴(조건절/참조 누락, hedge 재유입)을 발견하지 않음.
- DB 소스 포함 configuration의 negative control은 #22 live adapter 이후 별도
  표기(ISSUES-PLAN-DRAFT L76) — #11 완료 기준에서 명시적 제외.
- Issue #11은 구현 merge 후에도 소유자 post-merge 리뷰가 끝나기 전에는 완료로
  간주하지 않는다(#61/#62/#64/#65 선례). merge 자체는 사용자 명시 지시 대기
  (2026-08-22 워크플로 변경).

## 7. PR/merge 권장

**단일 PR 권장.** T-1(정책 정렬 문구)과 T-2(그 불변식의 기계 강제)는 하나의
계약 결합부다 — 분리 시 "필수라고 말하는 문구 + 강제하지 않는 validator" 또는 그
역의 혼합 계약 상태가 발생한다(본 저장소 "no mixed-contract state" 선례, #5/#6/#9).
파일 수도 작다(운영 2 + validator 1 + 테스트 2 + HANDOFF).

merge 순서: Track P 마지막 항목(#11)이며 이후 Track P 완결. 진행 중 병렬 브랜치
없음(open PR 없음 확인). 구현 브랜치는 최신 `main`에서 분기해 단일 PR로
squash-merge하되, **2026-08-22 워크플로 변경에 따라 PR 개설 + 리뷰 코멘트 게시 후
사용자의 명시적 merge 지시를 기다린다**(PR #65/#66 선례). merge 직전 `git log
<base>..HEAD` 재확인(#13 세션 타이밍 레이스 선례).
