# Issue #6 실행 계획 — skill execution contract 구현

작성일: 2026-08-22
기준 커밋: `ac110d0` (= `origin/main`, 본 워크트리 `hjung3113/issue6-plan` 분기점)
Canonical design: `docs/10-skill-execution-contract.md` (PR #36, squash `12fc687`)
상위 계획: `migration/ISSUES-PLAN-DRAFT.md` — P-R 레인 `(#7, #8) -> #6 -> #11`

이 문서는 (1) ISSUES-PLAN-DRAFT "구현 시작 전 체크" 7항목을 현재 `main` 기준으로
재확인한 결과와 (2) #6 구현의 실행 계획(DAG)을 담는다. 이 문서 자체는 구현이 아니며,
구현 승인 절차를 대체하지 않는다.

---

## 1. 게이트 체크 결과 (7항목 전부 확인, 블로커 없음)

모든 확인은 문서 예시가 아니라 현재 `main`(=본 브랜치 HEAD `ac110d0`)의 실제 파일
기반이다. 이 시점의 기본 상태: `python3 scripts/validate_scaffold.py` exit 0,
`python3 -m pytest scripts/tests/ -q` 321 passed, open PR 없음.

### 게이트 1 — canonical design 문서를 읽었는가 → 통과

`docs/10-skill-execution-contract.md`(212줄) 전문을 읽고 현재 `main`과 대조했다.

- 설계가 전제하는 문서/구현이 모두 실재: `docs/08-feature-artifact-validation.md`
  (canonical 파일명), `docs/templates/legacy-map.md`·`review.md` 포함 13개 템플릿,
  `docs/09-agent-skill-routing.md`(#7), `docs/10-command-execution-contract.md`(#5),
  `docs/10-agent-role-boundary.md`(#8), `docs/09-evidence-grade-transition-control.md`(#9
  설계, 구현 전 — 아래 게이트 3 참고).
- 설계의 skill routing matrix 9개 행이 실제 `.opencode/skills/` 9개 디렉터리와
  정확히 1:1 대응 (behavior-contract, db-migration-analysis, dll-boundary-analysis,
  evidence-grading, feature-migration, legacy-discovery, parity-verification,
  target-feature-design, uncertainty-management).
- 설계 요구 구조(`## Inputs`/`## Outputs`/`## Procedure`/`## Branches`/
  `## Done means` 순서)를 현재 충족하는 스킬은 0개 — 이것이 #6이 메우는 갭이며
  설계와 현황이 정합한다.
- `docs/01-architecture.md:65`가 routing(docs/09)과 execution contract(docs/10)을
  분리해 연결하고 있어 설계 배치도 정합.

### 게이트 2 — 이슈 본문의 stale recommendation을 그대로 구현하지 않는가 → 통과

이슈 #6 본문 대비 확정된 차이 (merged canonical design이 우선, 계획 원칙 1):

| 이슈 본문 권고 | 현재 설계의 판정 | 구현 시 지침 |
|---|---|---|
| "다른 8개 스킬에 if-then 최소 1개씩 적용" | 설계가 화장적 분기 거부(Adversarial finding 1). 분기는 missing/partial/contradictory/blocking 의미론을 가져야 함 | if-then 개수가 아니라 common branch semantics 충족 여부가 기준 |
| "`[입력]`/`[출력]` 표기, Issue #4/#5와 동일 패턴" | 설계는 `[Input]`/`[Output]` 영문 마커 + 단일 canonical path vocabulary(문서 내 `FEATURE_ROOT` 문법) 사용 | 문서 예시 경로 표기는 그대로 복사하지 않고 docs/08 canonical 이름 + command layer와 동일 placeholder 사용(§3 파생 판정 P-1) |
| "Issue #4/#5 경로 규약 확정을 먼저" | 이미 충족: #4는 PR #25, #5는 PR #62로 merge됨 | 선행조건 완료, 잔여 지시 없음 |

이슈가 작성될 당시 존재했던 7개 스킬 개별 관찰(판단근거 섹션)은 현재 파일과
미세하게 다르지만(예: legacy-discovery는 이미 `## Done means` 보유, 4개 스킬은 #7
구현으로 `## Primary artifact boundary`/`## Skill tie-break` 추가됨) 이 차이는
설계가 이미 반영하고 있다. stale 본문을 그대로 따르는 항목은 없다.

### 게이트 3 — 선행 contract가 실제 main에 구현되어 있는가 → 통과

#6의 직접 선행 3건(#5/#7/#8) 전부 구현·merge됨:

| 선행 | 구현 증거 | 현재 main에서 확인 |
|---|---|---|
| #5 command contract | PR #62 `ca3c564` + PR #63 `076d2a0` | 7개 command 파일이 6섹션 계약 보유, `validate_command_contract()`가 구조·argument grammar·canonical 경로 검증(본 세션 실행으로 green 확인) |
| #7 routing | PR #59 `1019e19` + 후속 | 8개 agent 전부 routing 3섹션 + Escalation(12-field STOP 위임), 4개 중첩 스킬에 `## Primary artifact boundary`/`## Skill tie-break` 실재 확인, `validate_agent_routing()`/`validate_skill_routing_contract()` green |
| #8 permission boundary | PR #58 `d1483a5` + PR #60 `b8456aa` | designer deny-by-default granular `edit` + `bash: deny` + `task: deny` (runtime 검증 포함, HANDOFF 기록) |

부가 선행(설계가 "보존"을 요구하는 나머지): #14 durable state(PR #57 `bc3b946`,
`validate_durable_state()` green), #13 STOP contract(PR #61 `9ffdacf`, managed block
+ `validate_stop_condition_contract()` green), #10 provenance(스킬 내 `[observed]`/
`[inferred]` 규칙 실재 확인).

#9(grade transition)는 **구현 전**이지만 #6 대비 선행이 아니다 — Track P merge
순서가 명시적으로 `#6 -> #9 -> #11`이며, #6 구현은 #9 설계 문서를 참조만 한다
(evidence-grading 행: "Follow `docs/09-evidence-grade-transition-control.md`").
문서 참조는 파일이 main에 존재하므로 성립한다. #6이 #9의 validator 구현을
필요로 하는 부분은 없다. #11도 동일하게 #6 이후(`parity-verification` 파일 공유).

### 게이트 4 — 사용자의 명시적 구현 승인 → 조건부 통과 (이번 세션은 구현 없음)

- `AGENTS.md` rule 13 (design gate) 유효.
- HANDOFF.md 최신 항목(2026-08-21): "**Rule-13 Track P/D authorization remains in
  effect and has not been revoked.**" + "Next Track P order per plan: `#6 -> #9 ->
  #11` ... #6 now has all three of its prerequisites merged (#5, #7, #8 ...) so it
  **can start immediately**".
- ISSUES-PLAN-DRAFT 원칙: "이 계획 문서 또는 PR의 merge만으로 승인됐다고 간주하지
  않는다."
- 종합: Track P standing authorization이 #1/#2/#14/#7/#8/#5/#13 구현 세션의
  근거로 계속 유효하며 #6이 다음 순서로 지명되어 있다. 다만 본 세션 지시는
  "체크 + 실행 계획 문서"로 한정되어 있으므로 **본 세션에서 구현 코드는 작성하지
  않는다**. #6 구현 세션의 dispatch(사용자가 구현 착수를 지시하는 행위)가
  per-scope 명시 승인 시점이며, 그 세션은 이 문서의 게이트 결과가 green임을
  재인용한 뒤 착수한다. 게이트 결과에 블로커가 없으므로 별도 승인 질의 항목은
  없다.

### 게이트 5 — 구현 범위가 acceptance criteria를 넘지 않는가 → 통과

범위 상한 = 설계의 "Implementation requirements for issue #6"(10개 항목) +
"Skill routing matrix" + Non-goals. 구체적으로:

- 변경: `.opencode/skills/*/SKILL.md` 9개 전부(한 패스, 혼합 계약 금지 — #5의
  "repository never runs under a mixed command contract"와 동일 원칙),
  `scripts/validate_scaffold.py`의 구조 검사 추가, 신규 테스트 파일.
- 비변경(Non-goals 열거): routing/#5 command/#8 permission 재설계, #9 grade
  transition 구현, #10 provenance 재정의, #11 judge self-check 변경
  (`parity-verification` rule 7의 "where practical" 문구는 #11 소관 — #6은
  현행대로 보존), #4 agent 절차 재작업, #15 잔여 템플릿 작업, docs/08 canonical
  파일/생명주기 변경, migration 애플리케이션 코드.

### 게이트 6 — 새 lock-in 결정 시 design gate 재오픈 근거 → 통과

재오픈 메커니즘이 3중으로 존재: ISSUES-PLAN-DRAFT 계획 원칙 2("설계 재개방 금지.
구현 중 새로운 lock-in 결정이 필요해지면 임의 결정하지 않고 해당 design gate를 다시
연다"), 설계 본문(Adversarial finding 8 + acceptance criteria "implementation-time
design changes reopen the gate instead of rewriting approved design post hoc"),
AGENTS.md rule 13. 본 계획 §5에 재오픈 트리거를 명시해 구현 세션에 전달한다.

### 게이트 7 — shared file merge 순서 → 통과

- 현재 open PR 없음, `.opencode/skills/`를 건드리는 진행 중 브랜치 없음.
- Track P 후속(#9, #11)은 #6 이후 merge: #9는 evidence-grading 스킬 +
  validate_scaffold.py를, #11은 parity-verification 스킬 + verifier를 공유한다.
  병렬 착수해도 merge는 #6 먼저.
- Track D(#18/#20/#22/#23)는 `scripts/db/` 중심이며 #22 live adapter만 이후에
  parity-verification/verifier 경로를 만진다 — 전부 #6 이후 시점이다.
- `scripts/validate_scaffold.py` 충돌 패턴: Track P 각 이슈가 isolated
  `validate_*()` 함수 + 집계 지점 1줄을 additively 추가(#5/#13/#7/#8/#14 선례,
  순차 merge 시 trivial concatenation). 본 계획도 동일 패턴을 지킨다(태스크 T-V1
  단독 소유, 스킬 태스크는 해당 파일 금지).

---

## 2. 현재 스킬 파일 상태 (구현 기준선)

| 스킬 | 현재 구조 | #6 구현 시 주요 작업 |
|---|---|---|
| behavior-contract | #7 routing 2섹션 + 시나리오 절차 1–11 + provenance(#10) 규칙 | 5섹션 재배치, 절차를 `[Input]`/`[Output]` 마커 붙은 번호단계로, Branches/Done means 신설. #7·#10 규칙 원문 보존 |
| evidence-grading | #7 routing 2섹션 + 등급/provenance 규칙 | 동일. `{feature-id}` → `<feature-id>` 정규화(P-1), #9 설계 문서 참조 유지 |
| uncertainty-management | #7 routing 2섹션 + 6단계 절차 | 동일. feature-card 업데이트 요청 vs docs/05 이중 destination 명시 |
| parity-verification | #7 routing 2섹션 + judge 입력/규칙 1–11 | 동일. **rule 7 "where practical" 절대 수정 금지(#11 소관)**, #22 관련 rule 4–5 보존 |
| legacy-discovery | Goal/Procedure(10단계)/Done means | Inputs/Outputs/Branches 신설(구조가 가장 가까움), LSR 참조·provenance 보존 |
| db-migration-analysis | 번호절차 1–7 + 금지문만 | 5섹션 전부 신설, matrix 행의 입력(legacy-map.md)·출력(db-dependency-report.md) 경로 명시 |
| dll-boundary-analysis | 검사항목 나열 + Output 4항 | 5섹션 전부 신설, feature/project 이중 destination 분기 명시 |
| target-feature-design | Cover 목록 + 조건문 1개 | 5섹션 신설, 기존 if-then을 Branches로 흡수, #8 designer 직접기록 제한 언급, PG/Alembic 요건 보존 |
| feature-migration | Preconditions + Procedure 10단계 | 5섹션 재배치(Preconditions는 Inputs로 흡수 또는 병존 — P-2), rule 13 명시적 구현 게이트 입력 유지 |

validator 구조(`scripts/validate_scaffold.py`, 2026줄): 이슈별 isolated 검사함수
패턴이 확립되어 있음 — `validate_agent_routing()`(L233),
`validate_skill_routing_contract()`(L290), `validate_command_contract()`(L476) 등.
집계는 `main()`(L2006: agent/skill routing)과 `collect_validation_errors()`(L1992:
command/artifact/state) 2곳. 신규 함수는 `validate_skill_routing_contract()` 바로
뒤(스킬 구조 검사 그룹)에 추가하고 `main()`의 오류 리스트에
`validate_skill_execution_contract()` 항을 더하는 것이 최근접 유사 검사
(`validate_skill_routing_contract`)와 동일한 배치다. 테스트는
`scripts/tests/test_command_contract.py`의 패턴(tmp root + 최소 스킬 트리 +
positive/negative)을 따르는 신규 파일 `test_skill_execution_contract.py`.

---

## 3. 파생 판정 사항 (신규 lock-in 아님 — 근거 명시)

구현 중 아래 판정은 임의 결정이 아니라 merged design에서 유도된다. 구현자/리뷰어가
유도 근거에 동의하지 않으면 그때만 design gate를 재오픈한다.

- **P-1. 스킬 파일 경로 placeholder를 `{feature-id}` → `<feature-id>`로 정규화.**
  근거: 설계 Goal("must reuse the same artifact vocabulary as the agent and command
  layers instead of creating a third independent path scheme") + command layer
  validator(`_FEATURE_PATH_RE`)가 이미 `<feature-id>`를 요구. 새 스킬 검사가 같은
  regex를 재사용하려면 스킬 파일도 동일 문법이어야 한다. 설계 문서 본문의
  `<FEATURE_ID>` 예시와도 충돌 없음(placeholder 표기 통일일 뿐).
- **P-2. 기존 섹션(`## Goal`, `## Primary artifact boundary`, `## Skill tie-break`,
  Preconditions 등)과 신규 5섹션의 배치.** 필수 5섹션의 **상대 순서**만 설계가
  요구하므로, 검사는 5섹션 상대 순서만 강제하고 절대 위치/추가 섹션은 자유로
  둔다. 권장 배치: 선택 계약(#7 섹션) → `## Inputs` → `## Outputs` →
  `## Procedure` → `## Branches` → `## Done means`. 근거: 설계가 "contain these
  sections in this order"로 5섹션만 열거, 다른 섹션 금지 없음.
- **P-3. 스킬 결과 라벨(`BLOCKED`/`PARTIAL`)과 agent STOP payload의 구분.**
  스킬의 BLOCKED/PARTIAL은 스킬 반환 결과 라벨(docs/10)이고, agent의 12-field
  STOP payload는 #13 계약이다. 스킬 파일에 STOP payload를 추가하지 않는다(중복
  taxonomy 생성 금지, 설계 adversarial finding 9의 "stricter or orthogonal
  controls 보존").
- **P-4. 구조 검사의 최소 결정론적 범위.** 설계가 "A deterministic scaffold check
  may verify that every SKILL.md has the required structural sections. Semantic
  correctness of a branch remains review work"로 명시했으므로, validator는
  §4-T-V1에 나열된 구조 검사만 하고 분기 문장의 의미론은 검사하지 않는다.

---

## 4. 태스크 분해 (DAG)

원칙: 논리적으로는 아래처럼 분해되나, 물리적으로는 **단일 브랜치/단일 PR에서 9개
스킬을 한 패스로 갱신**한다(#5 선례: 혼합 계약 상태 금지). 병렬 그룹은 리뷰
분업과 다수 worktree 작업 시 배분용이다. 다수 worktree를 쓰는 경우에도
`scripts/validate_scaffold.py`·테스트 파일은 T-V1 단독 소유로 지정해 shared-file
충돌을 원천 차단한다(#5/#13 세션의 확립된 패턴).

```text
T-0 (완료: 이 문서) 게이트 체크 + 실행 계획
     |
     v
[병렬 그룹 A]  T-V1 ∥ S-1..S-9   (파일 완전 분리)
     |
     v
T-I1 통합 검증 (validator + pytest + doc links)
     |
     v
T-R1 독립 adversarial review (구현자와 독립, AGENTS.md rule 10)
     |
     v
T-H1 HANDOFF.md 갱신 + Issue #6 구현 코멘트 + squash-merge PR
```

### 태스크 목록

| ID | 설명 | 대상 파일 | 선행 | 병렬 그룹 |
|---|---|---|---|---|
| T-0 | 게이트 7항목 재확인 + 본 실행 계획 작성·커밋 | `migration/ISSUE-6-EXECUTION-PLAN.md` | — | — (본 세션, 완료) |
| T-V1 | 구조 검사 추가: `validate_skill_execution_contract()` (9개 스킬 파일 대상 — ① 실재 ② 필수 5섹션 존재·비어있지 않음·상대 순서 ③ `## Procedure`에 `[Input]`/`[Output]` 마커 각 1개 이상 ④ feature 경로가 `<feature-id>` placeholder + canonical singleton 이름(기존 `_FEATURE_PATH_RE` 재사용) ⑤ legacy alias 거부 ⑥ `## Branches`에 `BLOCKED`/`PARTIAL` 중 1개 이상 언급) + `main()` 배선 + 테스트 파일(positive + negative 각 검사별) | `scripts/validate_scaffold.py`, `scripts/tests/test_skill_execution_contract.py`(신규) | T-0 | A |
| S-1 | behavior-contract 재구조: 5섹션, `[Input]`/`[Output]` 마커, matrix 행의 입출력 경로, common branch semantics. #7 섹션·#10 provenance 규칙 원문 보존 | `.opencode/skills/behavior-contract/SKILL.md` | T-0 | A |
| S-2 | evidence-grading 재구조: 동일. feature/project 이중 evidence destination, #9 설계 참조 유지 | `.opencode/skills/evidence-grading/SKILL.md` | T-0 | A |
| S-3 | uncertainty-management 재구조: feature-card 업데이트 요청 vs `docs/05-open-questions.md` 이중 destination 분기 | `.opencode/skills/uncertainty-management/SKILL.md` | T-0 | A |
| S-4 | parity-verification 재구조: **"where practical" 문구 포함 rule 7 현행 보존(#11 소관)**, PG guard rule 4–5 보존 | `.opencode/skills/parity-verification/SKILL.md` | T-0 | A |
| S-5 | legacy-discovery 재구조: Inputs/Outputs/Branches 신설, 기존 Goal/Procedure/Done means 흡수·정리, LSR 참조 유지 | `.opencode/skills/legacy-discovery/SKILL.md` | T-0 | A |
| S-6 | db-migration-analysis 재구조: 5섹션 전부 신설, 입력 `legacy-map.md`·출력 `db-dependency-report.md` 경로 명시 | `.opencode/skills/db-migration-analysis/SKILL.md` | T-0 | A |
| S-7 | dll-boundary-analysis 재구조: feature(`FEATURE_ROOT/dll-boundary-report.md`) vs project(`migration/evidence/dll-boundary-report.md`) 이중 destination 분기 | `.opencode/skills/dll-boundary-analysis/SKILL.md` | T-0 | A |
| S-8 | target-feature-design 재구조: 기존 단일 if-then을 Branches로 흡수, #8 designer 직접기록 제한 언급, lock-in 미해결 시 provisional/BLOCKED | `.opencode/skills/target-feature-design/SKILL.md` | T-0 | A |
| S-9 | feature-migration 재구조: Preconditions를 Inputs에 반영, 명시적 사용자 구현 게이트(rule 13) 입력 유지, code/test 경로는 승인된 설계가 선언한 경로만 | `.opencode/skills/feature-migration/SKILL.md` | T-0 | A |
| T-I1 | 통합 검증: `python3 scripts/validate_scaffold.py` exit 0, `python3 -m pytest scripts/tests/ -q` 전수 green(321 + 신규), `check_doc_links.py`/`check_oq_updates.py` green. 미달 시 수정 후 재실행 | (수정 대상 없음 — 검증 단계) | T-V1, S-1..S-9 | — |
| T-R1 | 독립 adversarial review: §6 완료 기준 대조, 특히 #7/#5/#8/#10/#13 보존 여부와 Non-goals 준수. 발견 사항은 merge 전 수정 | (리뷰 보고) | T-I1 | — |
| T-H1 | HANDOFF.md in-place 갱신(근거 SHA·테스트 수·잔여 불확실성 포함), Issue #6에 구현 코멘트, PR 생성 후 squash-merge. merge 후 소유자 리뷰 코멘트 추적(#61/#62 선례: merge 후에도 followup 필요할 수 있음) | `HANDOFF.md`, GitHub | T-R1 | — |

병렬성 요약: 그룹 A(T-V1 + S-1..S-9)는 10개 태스크 전부 서로소 파일이라 완전
병렬 가능. 단일 세션 실행 시 순서 권장: T-V1 → S-1..S-9(validator가 목표 구조를
먼저 확정해 스킬 편집의 정확한 기준이 됨) → T-I1.

---

## 5. 설계 게이트 재오픈 트리거 (구현 중 하나라도 걸리면 중단하고 기록)

1. §3의 파생 판정 P-1~P-4가 유도 근거 없이 무너진다고 판단되는 경우(예: command
   layer와 다른 placeholder 문법이 실제로 필요하다는 증거 발견).
2. 9개 스킬 중 어느 것이 matrix 행으로 표현 불가능한 고유 분기/경로를 요구하는
   경우(예: 새로운 project-wide destination이 필요).
3. 구조 검사가 의미론을 검사해야만 한다고 판단되는 경우(설계가 명시적으로
   review work로 남김 — machine-readable schema는 별도 설계).
4. #7 routing 섹션, #5 command 소유권, #8 쓰기 권한, #10 provenance, #13 STOP
   semantics 보존이 5섹션 구조와 양립 불가능하게 충돌하는 경우.
5. 그 외 "이슈 본문 권고를 그대로 구현해야 한다"는 유혹이 생기는 모든 순간
   (게이트 2 참조 — 본문은 stale).

재오픈 시 취할 행동: 해당 design gate(#6 또는 충돌하는 타 이슈 설계)를 열고,
`docs/05-open-questions.md` 또는 이슈 코멘트로 미결정 사항을 기록한 뒤 사용자
판단을 기다린다. 임의 결정 금지.

---

## 6. 검증/완료 기준

- 9개 스킬 전부가 필수 5섹션(상대 순서 준수) + `[Input]`/`[Output]` 마커 +
  canonical 경로 어휘를 갖고 `validate_skill_execution_contract()`가 green.
- 기존 검사 전부 잔존 green: `validate_skills()`, `validate_skill_routing_contract()`
  (4개 스킬 #7 섹션 보존 증명), `validate_command_contract()`,
  `validate_agent_routing()`, `validate_stop_condition_contract()`,
  `validate_durable_state()` 등 — 즉 `python3 scripts/validate_scaffold.py` exit 0.
- `python3 -m pytest scripts/tests/ -q` 전수 통과(321 baseline + 신규 테스트).
- `check_doc_links.py`, `check_oq_updates.py` 통과.
- 독립 리뷰(T-R1)가 Non-goals 위반·선행 계약 훼손·화장적 분기(gate 2의 stale
  권고 부활)를 발견하지 않음.
- 스킬 어느 곳도 STATE/QUEUE/lifecycle 갱신 권한을 스스로 주장하지 않음(구조
  검사 대상은 아니나 리뷰 체크리스트 항목).
- Issue #6은 구현 merge 후에도 #61/#62 선례에 따라 소유자 post-merge 리뷰가
  끝나기 전에는 완료로 간주하지 않는다.

## 7. merge 순서

#6 단일 PR. 이후 Track P는 `#9 -> #11` 순서 유지(#9, #11 모두 #6 결과물 위에서
작업). Track D는 #6과 무관하게 진행 가능하되 #22 live adapter가
parity-verification/verifier를 건드리는 시점은 #6(및 #11) merge 이후여야 한다.
