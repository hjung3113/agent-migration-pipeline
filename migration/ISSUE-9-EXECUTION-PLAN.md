# Issue #9 실행 계획 — evidence grade transition control 구현

작성일: 2026-08-23
기준 커밋: `325126b` (= `origin/main`, 본 워크트리 `hjung3113/issue9-plan` 분기점)
Canonical design: `docs/09-evidence-grade-transition-control.md` (A-7)
상위 계획: `migration/ISSUES-PLAN-DRAFT.md` — P-A 레인 `#1 -> #2 -> #9`, Track P merge 순서 8번
이슈 본문: GitHub Issue #9 "[A-7][Critical] 증거 등급 상향 방지 절차/이력 필드 부재" (본문 권고는 일부 stale — 게이트 2 참조)

이 문서는 (1) ISSUES-PLAN-DRAFT "구현 시작 전 체크" 7항목을 현재 `main` 기준으로
재확인한 결과와 (2) #9 구현의 실행 계획(DAG)을 담는다. 이 문서 자체는 구현이 아니며,
구현 승인 절차를 대체하지 않는다.

---

## 1. 게이트 체크 결과 (7항목 전부 확인, 블로커 없음)

모든 확인은 문서 예시가 아니라 현재 `main`(=본 브랜치 HEAD `325126b`)의 실제 파일
기반이다. 이 시점의 기본 상태(본 세션 실행으로 확인): `python3
scripts/validate_scaffold.py` exit 0, `python3 -m pytest scripts/tests/ -q` —
341 passed, open PR 없음.

### 게이트 1 — canonical design 문서를 읽었는가 → 통과

`docs/09-evidence-grade-transition-control.md`(240줄) 전문을 읽고 현재 `main`과
대조했다.

- 설계가 전제하는 3개 구현 대상이 모두 실재하며 설계가 묘사한 현황과 정합:
  `docs/templates/evidence-record.md`는 `Grade:` 단일 필드 + 6개 섹션(Evidence /
  Reproduction steps / Observation / Inference (optional) / Limitations /
  uncertainty / Related artifacts)뿐이고 grade-decision history 없음;
  `.opencode/skills/evidence-grading/SKILL.md`는 "do not upgrade a grade without
  new evidence" 산문 규칙만 있고 정렬된 compare-before-change 절차 없음; 전용
  transition 검사기 없음.
- 설계의 3-layer 구분(Layer 1 static schema / Layer 2 agent procedure /
  Layer 3 revision-aware transition)이 현재 validator 구조와 양립 가능함을
  확인(§2 참조).
- 설계의 "Existing-record adoption" 전제("no current data migration is needed")
  를 실제 저장소에서 재검증: `migration/evidence/`에는 `README.md`만 존재하고
  `migration/features/*/evidence/` 디렉터리 자체가 없다. 유일한 기록 파일인
  `migration/features/synthetic-demo/characterization-record.md`는 H1이
  `# Characterization:`로 evidence 인스턴스(`# Evidence:`)가 아니므로 #9 대상이
  아니다. 즉 설계 작성 시점 전제가 현재에도 성립한다(구현 직전 재확인 지침은
  §5 트리거 1).

### 게이트 2 — 이슈 본문의 stale recommendation을 그대로 구현하지 않는가 → 통과

이슈 #9 본문 대비 확정된 차이 (merged canonical design이 우선, 계획 원칙 1):

| 이슈 본문 권고 | 현재 설계의 판정 | 구현 시 지침 |
|---|---|---|
| 신규 레코드는 `?` 또는 `D`에서 시작 | 설계가 명시적으로 거부(Adversarial finding 1): `D`도 증거가 필요한 등급이며, 직접 관찰로 생성되는 레코드의 초기 `B`가 정당. 가짜 `? -> B` 전이 행은 실제 없었던 사건을 기록하게 됨 | 초기 등급은 생성 시점 실제 증거로 결정. 합성 전이 행 금지 |
| Grade history에 이전 등급/사유/링크 기록 (방향은 동일) | 설계가 스키마를 정밀화: 고정 컬럼 `Recorded date \| From \| To \| Reason \| Evidence refs`, 초기 행 `From = —`, 행간 연속성, `Grade:` == 마지막 행 `To` 불변식 포함 | 표 형식 자체가 아니라 설계의 불변식 전체를 구현 |
| #2 스크립트 확장 시 git diff 상향 감지해 "Grade history 갱신 여부" 경고 | 설계가 구조 분리를 명시(Adversarial finding 7 + Layer 3): enum/static 검증(#2)과 revision-aware 전이 검증은 별개 문제. 검사기는 base ref/SHA를 **명시적으로** 받아야 하고 임의 추론 금지 | `validate_evidence_record()`(static) 확장과 별도의 `--base <ref>`를 받는 독립 검사기로 분리(§3 P-2) |
| (본문 유의점) git log와 중복되지 않도록 why/what에 집중 | 설계가 동일 취지를 채택: 표가 author/commit을 중복 기록하지 않음 | 컬럼은 설계의 5개 그대로, author/commit 필드 추가 금지 |

본문의 문제 진단(원칙은 있으나 절차/데이터구조가 없다)은 설계가 그대로 승계했으므로,
stale 본문을 그대로 따르는 항목은 없다.

### 게이트 3 — 선행 contract가 실제 main에 구현되어 있는가 → 통과

#9의 직접 선행은 P-A 레인상 #2(A-2 artifact schema/reference validation, PR #56
`6d60cce`)이며 #1(PR #54/#55)도 완료. 현재 `main`의 `scripts/validate_scaffold.py`
에서 아래 요소를 전부 확인했다(줄번호는 `325126b` 기준):

| 선행 요소 | 위치 | 확인 내용 |
|---|---|---|
| `validate_evidence_record()` | L1183 | `# Evidence: <ID>` H1 인스턴스에 대해 header `- Key: value` 파싱, `Grade:`/`Source type:` enum, BR ref 검사. `validate_feature_schemas()`(L1320)가 feature 디렉터리 내 rglob으로 발견·호출 |
| `GRADES` | L837 | `("A", "B", "C", "D", "?")` — 설계의 enum과 동일 |
| `SOURCE_TYPES` | L840 | 8개 source type enum |
| `_parse_kv` / `_unique_fields` / `_split_sections` / `_visible_lines` / `_parse_tables` / `_cell` / `_err` | L977 / L987 / L949 / L894 / L914 / L939 / L1001 | Layer 1이 재사용할 파싱 인프라. 진단 형식 `path:line [category]` 통일 |
| Layer 1/3 비혼동 주석 | L829–832 | A-2 섹션 주석이 "no revision-aware grade history (#9)"를 명시적으로 Non-goal으로 남김 — #9가 이를 구현한다 |

부가 확인: A-2의 인스턴스 발견은 **feature 디렉터리 한정**이며 `migration/evidence/`
직속 파일은 오늘날 스캔 대상이 아니다(§3 P-8). #6(skill execution contract, PR #64
`5ef270d`)도 merge되어 evidence-grading 스킬이 이미 5섹션 계약 구조를 갖는다(§2) —
Layer 2 재작성은 이 구조를 보존하며 확장한다.

### 게이트 4 — 사용자의 명시적 구현 승인 → 조건부 통과 (이번 세션은 구현 없음)

- `AGENTS.md` rule 13 (design gate) 유효.
- HANDOFF.md 최신 항목(2026-08-22): "**Rule-13 Track P/D authorization remains
  in effect and has not been revoked.**" + "Next Track P order per plan: `#9 ->
  #11`" — Track P standing authorization이 issue-by-issue 구현의 근거로 #1/#2/#14/
  #7/#8/#5/#13/#6 세션에서 연속 적용되어 왔고 #9가 다음 순서로 지명되어 있다.
- ISSUES-PLAN-DRAFT 원칙: "이 계획 문서 또는 PR의 merge만으로 승인됐다고 간주하지
  않는다." **따라서 본 실행 계획 문서 자체가 구현 승인이 아니다.** 승인 근거는 오직
  위의 standing authorization이며, #9 구현 세션(사용자가 구현 착수를 지시하는 행위)
  이 이 게이트 결과가 green임을 재인용한 뒤 착수한다. 본 세션 지시는 "게이트 체크 +
  실행 계획 문서"로 한정되어 있으므로 **본 세션에서는 구현 코드를 작성하지 않는다.**
- 게이트 결과에 블로커가 없으므로 별도 승인 질의 항목은 없다.

### 게이트 5 — 구현 범위가 acceptance criteria를 넘지 않는가 → 통과

범위 상한 = 설계의 "Acceptance criteria" + "Test requirements for implementation"
+ "Implementation boundaries"(구현 단계가 변경 가능하다고 명시한 면). 구체적으로:

- 변경: `docs/templates/evidence-record.md`(`## Grade history` 추가),
  `.opencode/skills/evidence-grading/SKILL.md`(Layer 2 절차화),
  `scripts/validate_scaffold.py`(Layer 1 확장), 신규 `scripts/
  validate_grade_transition.py` + 테스트 파일들. 설계 "Implementation
  boundaries"가 열거한 구현 면(template/skill/validator/transition checker)과
  정확히 일치.
- 비변경(Non-goals): 등급 값/의미 변경(docs/03 소유), characterization 기록의
  `Record grade rollup`·verification.md 등급 스키마 확장(설계가 evidence record로
  범위 한정), 기존 기록 정규화(대상 없음 — 게이트 1), CI 신규 job(§3 P-3, 설계가
  요구하지 않음), `.opencode/commands/*` 변경(필요 요건 없음), migration 애플리케이션
  코드, A-2의 인스턴스 발견 범위 확장(§3 P-8).

### 게이트 6 — 새 lock-in 결정 시 design gate 재오픈 근거 → 통과

재오픈 메커니즘이 3중으로 존재: ISSUES-PLAN-DRAFT 계획 원칙 2("설계 재개방 금지.
구현 중 새로운 lock-in 결정이 필요해지면 임의 결정하지 않고 해당 design gate를 다시
연다"), 설계 본문("Implementation boundaries" — 구현 변경은 rule 13 게이트 하에
있음), AGENTS.md rule 13. 본 계획 §5에 재오픈 트리거를 명시해 구현 세션에 전달한다.

### 게이트 7 — shared file merge 순서 → 통과

- 현재 open PR 없음(`gh pr list` 확인), 본 이슈 파일들을 건드리는 진행 중 브랜치 없음.
- `git log --oneline -20`: 최근 merge는 #6(`5ef270d`)까지. Track P 후속 #11은
  `parity-verification` 스킬 + verifier를 공유하나 #9의 파일(evidence-grading 스킬,
  evidence-record 템플릿)과 겹치지 않는다. Track D(#18/#20/#22/#23)는 `scripts/db/`
  중심으로 무관.
- `scripts/validate_scaffold.py` 충돌 패턴: Track P 각 이슈가 isolated
  `validate_*()` 함수를 additively 추가해 온 것(#5/#7/#8/#13/#14/#6 선례)과 달리,
  #9는 기존 `validate_evidence_record()` **내부를 확장**한다. 다만 해당 함수를
  수정하는 다른 진행 중 작업이 없으므로(위 확인) 순차 단일 PR이면 충돌 없음.
  Layer 3은 별도 신규 파일이므로 `collect_validation_errors()`/`main()` 배선을
  건드리지 않는다(§3 P-2).
- #6 세션의 F1/F2 교훈(batch 구조 재작성이 조건절/참조를 조용히 누락)이 #9의
  T-L2(스킬 재작성)에 직접 적용된다 — §4 T-L2에 보존 체크리스트로 명시.

---

## 2. 현재 구현 기준선 (구현 세션이 기대해야 하는 출발 상태)

### `docs/templates/evidence-record.md` (31줄)

H1 `# Evidence: <ID>`, header 필드 `Feature/Rule/Scenario/Grade/Captured
date/Source type`, 섹션 `Evidence/Reproduction steps/Observation/Inference
(optional)/Limitations / uncertainty/Related artifacts`. `## Grade history` 없음.
A-2는 `docs/templates/`를 인스턴스로 취급하지 않으므로 템플릿 변경은 validator를
통과 못 하는 상태를 만들지 않는다.

### `.opencode/skills/evidence-grading/SKILL.md` (97줄, #6/#7 구조)

섹션 순서: `## Primary artifact boundary`(#7) → `## Skill tie-break`(#7) →
`## Inputs` → `## Outputs` → `## Procedure`(6단계, `[Input]`/`[Output]` 마커 포함)
→ `## Branches`(BLOCKED/PARTIAL 포함) → `## Done means` → `## Grading rules`.
`validate_skill_execution_contract()`가 5개 필수 섹션의 존재·순서·마커·경로
어휘를 검사한다 — Layer 2 재작성은 이 검사를 항상 green으로 유지해야 한다.
`## Inputs`에 이미 `docs/09-evidence-grade-transition-control.md` 참조가 있다
(check_doc_links 대상). `## Grading rules`의 등급 뜻(A/B/C/D/?)·provenance
(observed/inferred) 규칙은 docs/03이 소유한 내용의 스킬 표현으로 보존 대상.

### `scripts/validate_scaffold.py` (2176줄)

A-2 섹션(L829–1367)이 enum/ID/reference 검증을 소유. `validate_evidence_record()`
는 `_split_sections` 결과 `_sections`를 현재 버린다(`_header, _sections = ...`) —
Layer 1 확장이 이를 사용해 `## Grade history` 섹션을 찾고 `_parse_tables`로 표을
읽으면 된다. 집계 경로: `validate_feature_schemas()` ← `collect_validation_errors()`
← `main()` — Layer 1은 호출점·발견 로직 불변, 함수 내부 확장만으로 배선 완료.
크로스-스크립트 import 선례: L7–14가 `scripts/sync_agent_stop_conditions.py`를
try/except로 import — Layer 3이 parser helper를 역방향(신규 스크립트가
validate_scaffold를 import)으로 재사용하는 패턴 근거.

### 증거 인스턴스 현황

`migration/evidence/` = README.md only. `migration/features/` = synthetic-demo 1개,
`evidence/` 서브디렉터리 없음. 즉 Layer 1 신규 검사가 grep하는 실제 인스턴스는
0개 — 새 검사가 오늘날 저장소를 깨뜨리지 않는다(템플릿은 비인스턴스).

### CI (`.github/workflows/ci.yml`)

`repo-guards` job: scaffold validation + `check_oq_updates.py` + `check_doc_links.py`
(checkout `fetch-depth: 2`, push/PR 트리거). pytest는 CI에서 실행되지 않고
로컬/리뷰 회귀용. PR-diff 기반 job이나 base-ref 해석 인프라는 없음 → §3 P-3.

---

## 3. 파생 판정 사항 (신규 lock-in 아님 — 근거 명시)

구현 중 아래 판정은 임의 결정이 아니라 merged design에서 유도된다. 구현자/리뷰어가
유도 근거에 동의하지 않으면 그때만 design gate를 재오픈한다.

- **P-1. Layer 1은 `validate_evidence_record()` 확장(내부 helper `_validate_
  grade_history()` 추가)이지 sibling 최상위 함수가 아니다.** 근거: 설계 Layer 1이
  "This can share parsing conventions with Issue #2's enum/schema validation work"
  로 명시. 동일 단일-파일-상태 관심사, 동일 H1-발견 호출점
  (`validate_feature_schemas`), `_parse_tables`/`_cell`/`_split_sections`/`_err`
  재사용. sibling은 발견·header 파싱을 중복하게 된다.
- **P-2. Layer 3은 신규 독립 엔트리포인트 `scripts/validate_grade_transition.py`
  이며 `collect_validation_errors()`/`main()`이 무조건 호출하지 않는다.** 근거:
  설계 Adversarial finding 7 + Layer 3("it must receive a base ref/SHA rather than
  infer one silently"). 단일 트리 scaffold 검사에는 두 번째 revision이 없으므로
  기존 파이프라인에 넣는 순간 base 추론을 강제하게 된다. 스키마 검증(#2)과
  반-은닉-상향 검증의 분리는 acceptance criteria("static schema validation and
  revision-aware transition validation are separated cleanly") 자체다.
- **P-3. Layer 3 호출 방식 = 명시적 CLI.** `--base <ref>` (필수, 기본값 없음),
  `--file <path>` (반복 지정, 검사 대상 evidence-record 파일), head 측 기본값은
  작업 트리 파일, 선택 인자 `--head <ref>`로 대상 revision 지정. 근거: 작업
  프롬프트가 예시로 제시한 형태 그대로이며 "never infer one"을 구조적으로 보장
  (기본값 부재). CI job 추가는 하지 않는다 — 설계는 CI를 요구하지 않고(구현 면으로
  "남겨둔" 목록에만 있음), repo-guards는 `fetch-depth: 2` 단일 트리 검사라 PR-diff
  job은 신규 인프라가 된다(YAGNI). 호출 안내는 스크립트 docstring + HANDOFF +
  T-R1 리뷰 체크리스트에 기록하고, CI 강제를 원할 경우 별도 후속으로 사용자에게
  확인한다(§5 트리거 4).
- **P-4. Layer 2의 문서 구조.** 기존 `## Grading rules`(등급 뜻·provenance 규칙,
  docs/03 소유 내용)은 보존하고, 그 옆에 전용 `## Grade-change procedure` H2를
  신설해 설계의 8단계 절차를 번호 단계로 넣는다. `## Inputs`/`## Outputs`/
  `## Procedure`에는 `## Grade history`를 읽고/붙이는 최소한의 추가 언급만 넣는다
  (Inputs: 기존 기록의 grade history 포함; Outputs/Procedure: 전이 시 history 행
  append). 5개 필수 섹션의 상대 순서와 `[Input]`/`[Output]` 마커, BLOCKED/PARTIAL
  언급은 그대로(validator가 강제). 근거: 설계 Layer 2가 "Rewrite ... from a prose
  reminder into the numbered compare-before-change procedure"를 요구하면서 #6/#7
  구조 파괴를 허용하지 않음. 섹션 삭제 없음, 조건절·문서 참조(#6 F1/F2 패턴) 보존
  체크리스트로 검증.
- **P-5. Layer 2의 기계 검증 수위.** 스킬 내용에 대한 신규 테스트는 결정론적
  문자열 존재 검사로 한정한다(8단계 절차 존재, "unresolved contradictory evidence
  blocks promotion" 계열 문장, promotion 신규 증거 요구 문장, 과거 결론 삭제 금지
  문장) — `scripts/tests/test_skill_execution_contract.py`에 evidence-grading 한정
  추가. 의미론(예: `-> A` 독립성 판단)은 review work로 남긴다(docs/10 경계:
  "Semantic correctness of each branch remains review work"). 근거: #6 리뷰 F10의
  과도 경화 반성 및 docs/10 계약.
- **P-6. Layer 1 상세 스키마 결정.** 설계가 불변식 목록만 주고 바이트 수준 형식은
  못 정한 항목: ① 표 헤더는 고정 컬럼 `Recorded date | From | To | Reason |
  Evidence refs`와 정확히 일치(작업 정의가 "fixed columns"로 명시) ② 초기 행
  `From`은 em-dash `—` 정확히(오류 메시지가 기대 형태를 제시) ③ `Recorded date`는
  `YYYY-MM-DD` 형식 검사(설계 예시 형식, `validate_durable_state`의 timestamp
  검사 선례와 동일 수위) ④ `Reason`은 모든 행에서 비어있으면 안 됨(설계 불변식)
  ⑤ `Evidence refs`는 비초기 행 전부 + 초기행 중 `To != ?`인 행은 비어있으면 안 됨
  — `?`는 "no usable evidence yet"이므로 초기 `?`의 refs 부재는 정당(설계 Initial
  grading에서 유도) ⑥ `## Grade history`가 존재하는 인스턴스에서는 header `Grade:`
  필드가 필수가 됨(등식 불변식이 존재를 함의).
- **P-7. Layer 3 상세 의미 결정.** ① append-only: base의 history 행렬이 candidate
  의 접두(prefix)여야 함 ② "새 증거 참조" = append된 promotion 행의 refs 중 base
  revision 파일 본문 어디에도 등장하지 않는 토큰(작업 정의 "not present in the
  prior revision" 문구 그대로) ③ 두 revision 사이 evidence-record 파일 삭제는
  오류 처리("record replacement must not bypass history", 설계 finding 8) —
  리뷰에서 정당한 삭제로 판명되면 리뷰 단계에서 면제 가능 ④ base에 history 없는
  legacy 기록은 candidate의 history가 설계의 adoption baseline 행(`— -> <base
  시점 Grade>`)으로 시작해야 함 ⑤ 등급 서열 맵 `? < D < C < B < A`(설계 "Grade
  ordering")로 promotion/downgrade 판정. 전부 설계 각 절에서 직접 유도.
- **P-8. Layer 1 적용 범위는 A-2의 현행 발견 범위(feature 디렉터리)를 따른다.**
  `migration/evidence/` 직속 인스턴스는 오늘날 A-2가 스캔하지 않으며(§1 게이트 3),
  발견 범위 확장은 #2 소유 schema-discovery 결정이다(#9가 임의로 바꾸지 않음).
  Layer 3은 `--file`에 임의 경로를 받으므로 project-wide 기록도 검사 가능 — 이
  비대칭을 HANDOFF에 기록한다. project-wide 인스턴스가 실제 생기면 그때 #2 설계에
  발견 범위 질의(§5 트리거 5와 동일 프로세스).

---

## 4. 태스크 분해 (DAG)

원칙: Layer 1/2/3 태스크는 파일이 완전 분리되어 병렬 가능하다. 물리적으로는 **단일
브랜치/단일 PR**로 출하한다(§7). 다수 worktree 병렬 실행 시에도 각 태스크의 파일
소유권이 겹치지 않아 shared-file 충돌이 없다.

```text
T-0 (완료: 이 문서) 게이트 체크 + 실행 계획
     |
     v
[병렬 그룹 A]  T-L1 ∥ T-L2 ∥ T-L3   (파일 완전 분리)
     |
     v
T-I1 통합 검증 (validator + 전수 pytest + doc links/OQ + L3 smoke run)
     |
     v
T-R1 독립 adversarial review (구현자와 독립, AGENTS.md rule 10)
     |                              — #6 세션의 2단계(PR 본문 → diff) 패턴 재사용
     v
T-H1 HANDOFF.md 갱신 + Issue #9 구현 코멘트 + squash-merge PR + merge 후 소유자 리뷰 추적
```

### 태스크 목록

| ID | 설명 | 대상 파일 | 선행 | 병렬 그룹 |
|---|---|---|---|---|
| T-0 | 게이트 7항목 재확인 + 본 실행 계획 작성·커밋 | `migration/ISSUE-9-EXECUTION-PLAN.md` | — | — (본 세션, 완료) |
| T-L1 | **Layer 1**: ① 템플릿에 `## Grade history` 추가(고정 컬럼 + 지시 문구; 인스턴스가 아니므로 validator 무관) ② `validate_evidence_record()` 확장 + `_validate_grade_history()` helper: history 섹션 존재·≥1 행, 헤더 고정 컬럼 일치, 초기 행 `From = —`, 행간 `From`/`To` 연속성, `From`/`To` enum(초기 `From` 제외), `Grade:` == 마지막 행 `To`(history 있으면 `Grade:` 필수), `Reason` 비어있지 않음, refs 규칙(P-6 ⑤), 날짜 형식(P-6 ③) ③ 테스트: 신규 `scripts/tests/test_grade_history.py` — 설계 Test requirements의 L1 항목 커버(§6 매핑) | `docs/templates/evidence-record.md`, `scripts/validate_scaffold.py`, `scripts/tests/test_grade_history.py`(신규) | T-0 | A |
| T-L2 | **Layer 2**: `evidence-grading/SKILL.md` 재작성 — `## Grading rules` 보존 + `## Grade-change procedure` H2 신설(설계 8단계: 기존 기록 탐색/갱신 우선 → 현 Grade·history·참조·limitations 통독 → 증거 먼저 확보·목표 등급 나중 → 최고 정당 등급 재평가·미해결 모순은 promotion 차단 → 등급 불변 시 history 행 추가 금지 → 등급 변경 시 행 append(promotion은 신규 증거 참조, downgrade는 모순/무효화 사유) → `Grade:` 동시 갱신·말행 `To`와 일치 → 과거 결론 삭제 금지·역방향은 새 전이로 기록) + Inputs/Outputs/Procedure의 history 언급 최소 추가. 보존 체크리스트(#6 F1/F2 교훈): 5섹션 순서·마커·BLOCKED/PARTIAL, #7 양 섹션, #10 provenance 규칙, #8 읽기전용 persistence 위임, #13 STOP 위임, `docs/09`/`docs/templates` 참조 링크, 모든 조건절 원문. 테스트: `test_skill_execution_contract.py`에 evidence-grading 한정 내용 존재 검사(P-5) | `.opencode/skills/evidence-grading/SKILL.md`, `scripts/tests/test_skill_execution_contract.py` | T-0 | A |
| T-L3 | **Layer 3**: 신규 `scripts/validate_grade_transition.py` — `--base <ref>` 필수·기본값 없음, `--file` 반복, head 기본 작업 트리/`--head <ref>` 선택. 동작: base 내용 `git show`로 취득, 양쪽을 validate_scaffold parser(try/except import, L7–14 선례)로 파싱, ① 신규 기록(base에 없음)은 초기 행 불변식만(`?` 사전 등급 발명 금지) ② 기존 기록: Grade 변경 시 append 행 요구·prefix 보존·경계 연속성·최종 `To` == candidate `Grade:` ③ promotion(서열 맵)마다 base 파일에 없는 신규 refs ≥1 ④ 등급 불변 시 append 행 있으면 오류(합성 전이) ⑤ 삭제 오류(finding 8) ⑥ legacy adoption baseline(P-7 ④). 진단 `path:line [category]`, 오류 시 non-zero exit. 테스트: 신규 `scripts/tests/test_grade_transition.py` — 임시 git 저장소 fixture(git 부재 시 skip), 설계 Test requirements의 L3 항목 + `--base` 누락 = 오류(§6 매핑) | `scripts/validate_grade_transition.py`(신규), `scripts/tests/test_grade_transition.py`(신규) | T-0 | A |
| T-I1 | 통합 검증: `python3 scripts/validate_scaffold.py` exit 0, `python3 -m pytest scripts/tests/ -q` 전수 green(341 + 신규), `check_doc_links.py`/`check_oq_updates.py` green, L3 smoke(합성 before/after 기록 쌍으로 valid promotion / promotion-무-증거 각각 exit 0/1 확인). 미달 시 수정 후 재실행 | (수정 대상 없음 — 검증 단계) | T-L1, T-L2, T-L3 | — |
| T-R1 | 독립 adversarial review: §6 완료 기준 대조. 특히 (a) #6 F1/F2 패턴 — T-L2 재작성이 조건절/참조를 누락했는지 pre/post diff 대조 (b) Layer 1이 `?` 초기 등급·adoption baseline을 합성 전이로 오탐하는지 (c) Layer 3이 base를 추론하거나 single-tree 파이프라인에 혼입되지 않았는지 (d) Non-goals 준수 (e) 이슈 본문 stale 권고 부활 없음. 발견 사항은 merge 전 수정 | (리뷰 보고) | T-I1 | — |
| T-H1 | HANDOFF.md in-place 갱신(근거 SHA·테스트 수·L3 호출법·§6 잔여 불확실성 포함), Issue #9에 구현 코멘트, PR 생성 후 squash-merge. merge 후 소유자 리뷰 코멘트 추적(#61/#62/#64 선례: merge 후에도 followup 필요할 수 있음) | `HANDOFF.md`, GitHub | T-R1 | — |

병렬성 요약: 그룹 A(T-L1/T-L2/T-L3)는 3개 태스크 전부 서로소 파일이라 완전 병렬
가능. 단일 세션 실행 시 순서 권장: T-L1 → T-L3 → T-L2(스키마(L1)가 전이 검사(L3)와
스킬 절차(L2)의 대상 형식을 먼저 확정) → T-I1.

---

## 5. 설계 게이트 재오픈 트리거 (구현 중 하나라도 걸리면 중단하고 기록)

1. **실제 evidence 인스턴스 발견.** 구현/리뷰 중 `migration/evidence/<id>.md` 또는
   `migration/features/*/evidence/*.md`에 `# Evidence:` H1 기록이 존재하는 것을
   발견하면(본 계획 확인 시점엔 0개), 설계의 "no current data migration is needed"
   전제가 stale해진 것이다. 기존 기록 normalization은 acceptance 범위 밖이므로
   adoption baseline 일괄 적용 여부·범위를 사용자에게 묻고 착수한다.
2. §3의 파생 판정 P-1~P-8의 유도 근거가 무너진다고 판단되는 경우(예: 설계가 의도한
   것과 다른 refs 요구 수위가 필요하다는 증거 발견).
3. T-L2 재작성이 #6 5섹션 계약, #7 routing 섹션, #8 읽기전용 persistence 위임,
   #13 STOP 위임과 양립 불가능하게 충돌하는 경우(구조 충돌은 설계가 예측하지 않음).
4. Layer 3를 single-tree scaffold 검사(CI repo-guards 등)에 통합해야 한다는 요구가
   생긴 경우 — base 추론 금지(설계 finding 7)와 직결되므로 임의 타협 금지. CI
   강제를 원하면 PR-diff job 설계를 별도 승인으로 받는다(P-3).
5. grade transition 통제가 characterization 기록(`Record grade rollup`)이나
   verification.md 등급으로 확장되어야 한다는 발견 — 설계는 evidence record로 범위
   한정. 범위 확장은 신규 설계 질문.
6. 그 외 "이슈 본문 권고를 그대로 구현해야 한다"는 유혹이 생기는 모든 순간(게이트 2
   — 본문은 stale: 강제 `?`/`D` 시작, #2 스크립트 내 경고 모두 형식만 다르고
   설계가 거부한 방향).

재오픈 시 취할 행동: 해당 design gate(#9 또는 충돌하는 타 이슈 설계)을 열고,
`docs/05-open-questions.md` 또는 이슈 코멘트로 미결정 사항을 기록한 뒤 사용자 판단을
기다린다. 임의 결정 금지.

---

## 6. 검증/완료 기준

설계 "Test requirements for implementation" 14개 항목의 레이어별 매핑:

| 설계 테스트 요건 | 담당 |
|---|---|
| 유효 등급 각각으로 직접 초기화(합성 전이 없음) | T-L1(단일 `— -> X` 행) + T-L3(신규 기록 모드) |
| 잘못된 등급/history enum | T-L1 |
| history 없음 | T-L1 |
| 초기 행의 invalid `From` | T-L1 |
| 끊어진 행간 체인 | T-L1 |
| `Grade:` != 마지막 행 `To` | T-L1 + T-L3(candidate 측) |
| 신규 증거 참조 포함 유효 promotion | T-L3 |
| 신규 증거 참조 없는 promotion | T-L3(오류) |
| 모순/무효화 사유 포함 유효 downgrade | T-L3(+T-L1 사유 비어있지 않음) |
| 등급 불변 + 증거 추가 + 합성 history 행 없음 | T-L3(append 행 있으면 오류) + T-L2 절차 5단계 |
| 미해결 모순의 promotion 차단 (스킬/프로세스 수위) | T-L2 내용 검사 + T-R1 리뷰 체크리스트 |
| `-> A` 독립성 의미론 (review 수위) | T-R1 리뷰(기계화하지 않음 — P-5) |
| legacy baseline adoption (과거 전이 날조 없음) | T-L3(P-7 ④) |
| revision-aware 비교가 명시적 base를 받음 | T-L3(`--base` 누락 = 오류, 기본값 없음) |

추가 완료 기준:

- `python3 scripts/validate_scaffold.py` exit 0 — Layer 1이 기존 검사(A-1/A-2/
  durable state/STOP/skill/command) 전부와 공존. 오늘날 인스턴스 0개이므로 신규
  검사는 저장소를 깨뜨리지 않아야 함(깨뜨리면 §5 트리거 1 상황).
- `python3 -m pytest scripts/tests/ -q` 전수 통과(341 baseline + 신규).
- `check_doc_links.py`, `check_oq_updates.py` 통과.
- T-L2 스킬이 `validate_skill_execution_contract()`·`validate_skill_routing_
  contract()`·`validate_skills()` 전부 green 유지(구조 회귀 없음).
- 독립 리뷰(T-R1)가 Non-goals 위반·선행 계약 훼손·stale 권고 부활·#6 F1/F2 패턴
  (조건절/참조 누락)을 발견하지 않음.
- Issue #9는 구현 merge 후에도 #61/#62/#64 선례에 따라 소유자 post-merge 리뷰가
  끝나기 전에는 완료로 간주하지 않는다.

## 7. PR/merge 권장

**단일 PR 권장.** 파일 집합이 작고(템플릿 1 + 스킬 1 + validator 1 + 신규 스크립트/
테스트 3 + HANDOFF) 3개 레이어가 하나의 설계 계약으로 결합되어 있어 분리 시 혼합
계약 상태(예: history 없는 템플릿 + history 요구 validator)가 발생한다 — 본 저장소의
"no mixed-contract state" 선례(#5/#6)와 일치. 분리 근거(독립 scope, 독립 리스크,
파일 소유 충돌)가 실재하지 않으므로 다중 PR로 쪼개지 않는다.

merge 순서: Track P는 `#9 -> #11` 유지. #11은 parity-verification/verifier를
공유하나 #9 파일과 무관. Track D는 #9와 무관하게 진행 가능. 구현 브랜치는 최신
`main`에서 분기해 rebase 없이 단일 PR로 squash-merge하고, merge 전 `git log
<base>..HEAD`를 재확인한다(#13 세션의 타이밍 레이스 선례).
