# Issues Plan Draft — 오픈 이슈 15건 + S-001~S-011 재설계 통합 계획

작성일: 2026-08-18
전제: AGENTS.md #13(design gate) 적용 — lock-in 위험 "중" 이상 항목은 설계 산출물만 만들고 멈춘다. 이 문서 자체도 계획(설계 준비) 산출물이며, 사용자 승인 전까지 구현을 디스패치하지 않는다.

## 범위

- Track 0: HANDOFF.md가 이미 지시한 S-001~S-011 재설계(design-only) — 별도 트랙으로 존재, 여기서는 다른 두 트랙과의 우선순위 관계만 정리
- Track P: 프로세스/에이전트 설정 하드닝 (오픈 이슈 #1,2,5,6,7,8,9,11,13,14 — 전부 A-시리즈)
- Track D: DB 도구 신설 (오픈 이슈 #18,20,21,22,23 — DB-Tooling 시리즈)

Track P/D는 레거시 접근 불필요, Track 0와도 독립적으로 병행 가능. 세 트랙 내부 순서만 의존성 있음.

## Track P — 프로세스/에이전트 설정 하드닝

| ID | 이슈 | 제목 | 난이도 | lock-in위험 | 설계게이트 | 선행 |
|---|---|---|---|---|---|---|
| P-001 | #11 (A-9, Critical) | parity-verification/verifier judge 자기검증 "where practical" 제거, negative control 필수 단계화 | 간단 | 하 | 불요(프로즈 강화, 즉시 적용 가능) | 없음 |
| P-002 | #14 (A-12, High) | STATE.md/QUEUE.md 기계 파싱 포맷·필드 enum 확정 | 보통 | 중 | **필요** — RULEBOOK 또는 신규 문서에 필드/enum 규약 명시 후 스크립트/문서 반영 | 없음 |
| P-003 | #9 (A-7, Critical) | evidence-record.md Grade history 필드 + 상향 절차 | 간단 | 중 | **필요** — 템플릿에 추가할 필드 구조를 먼저 확정(표 컬럼 정의) | 없음 |
| P-004 | #2 (A-2, High) | enum/ID 포맷 검증 스크립트 확장 | 보통 | 중 | **필요** — 검증 대상 enum/ID 패턴 전체 목록을 먼저 확정 | P-002, P-003 (검증할 필드/값이 이 두 결정에 좌우됨) |
| P-005 | #1 (A-1, Critical) | validate_scaffold.py에 feature 단위 필수 산출물 검증 추가 | 보통 | 중 | **필요** — feature 디렉토리 네이밍 규칙 확정 + Status별 필수 파일 매핑표 | P-004 (순회 로직 재사용) |
| P-006 | #13 (A-11, High) | 8개 agent md에 stop condition 재게시 + STOP 시 파일 단위 행동 명시 | 보통 | 중 | **필요** — "STOP 시 행동" 표준 절차(OQ 추가→feature Status 변경→STATE 갱신→상위 반환)를 한 곳에 정의 후 8곳에 적용 | P-002(Status enum), P-005(feature Status 필드) |
| P-007 | #5 (A-4+A-13, High) | 커맨드 7종에 Output/Preconditions/State updates 섹션 추가 | 보통 | 중 | **필요** — 출력 경로 템플릿·State updates 표기 규약을 한 번 정의 후 7개 파일에 일관 적용 | P-002(enum 값) |
| P-008 | #6 (A-4, Medium) | 스킬 9종에 입출력 경로 + if-then 분기 추가 | 보통 | 하 | 불요(target-feature-design 기존 패턴을 그대로 확장) | P-007 (경로 규약 일치 필요) |
| P-009 | #7 (A-5, High) | 스킬 4종 배타 트리거 문구 + agent 7종 escalation 문구 | 간단 | 하 | 불요(문구 추가) | 없음(병행 가능) |
| P-010 | #8 (A-6, Medium) | migration-designer 편집 범위를 문서로 명시 제한 | 간단 | 하 | 불요 | 없음(병행 가능) |

### Track P 권장 순서

1. **즉시 병행 가능(설계게이트 없음)**: P-001, P-009, P-010
2. **설계 먼저**: P-002 → P-003 (병행 가능, 서로 독립)
3. P-002·P-003 승인 후 → P-004
4. P-004 승인 후 → P-005
5. P-002 + P-005 승인 후 → P-007 → P-008
6. P-002 + P-005 승인 후 → P-006

## Track D — DB 도구 신설

| ID | 이슈 | 제목 | 난이도 | lock-in위험 | 설계게이트 | 선행 |
|---|---|---|---|---|---|---|
| D-001 | #23 (High) | DB 자격증명/연결 프로필 명명 규약 (`.env.example`, gitignore, docs/06 결정 기록) | 간단 | 중 | **필요** — 프로필 이름 집합(`prod-readonly`/`test-readwrite`/`pg-test-readwrite` 등) 확정을 docs/06에 기록 | 없음, 다른 D-항목 전부의 선행 |
| D-002 | #20 (Critical) | 위험 DB 동작(INSERT/UPDATE/EXEC) 테스트 DB 강제 라우팅 가드 | 복잡 | **상** | **필요, 별도 ADR** — 가드 모듈의 실행 시점(연결 시 vs 구문 파싱 시), 예외 처리, 프로필-호스트 매핑 검증 로직을 ADR로 남긴 뒤 시작 | D-001 |
| D-003 | #18 (High) | MSSQL 읽기전용 조회 도구 (`scripts/db/mssql_inspect.py`) | 보통 | 중 | **필요** — 출력 스키마(마크다운/JSON), legacy-map.md 삽입 형식을 먼저 정의 | D-001, D-002(가드 통과 원칙) |
| D-004 | #22 (High) | DB Before/After 스냅샷·Diff 도구 (`scripts/db/db_snapshot_diff.py`) | 복잡 | 중 | **필요** — MSSQL/PostgreSQL 공통 커넥터 추상화 + closed #12(비교 의미론) 규칙을 어떻게 읽어들이는지 인터페이스 정의 | D-001, D-002, 이미 해결된 이슈 #12(비교 의미론, `behavior-contract.md` Comparison semantics) |
| D-005 | #21 (Medium) | PostgreSQL 테스트 DB 부트스트랩/마이그레이션 도구 | 보통 | 중 | **필요하나 지연 가능** — 이슈 작성자도 Phase 3~4 실질 필요 시점으로 명시. Alembic 채택 여부만 지금 docs/06 "Defer" 항목에 기록해두고 실제 설계는 뒤로 미룸 | D-001 |

### Track D 권장 순서

1. D-001 (선행 필수, 다른 모두의 기반)
2. D-002 (D-001 승인 즉시 착수 — Critical, blast radius 최대)
3. D-003 (D-002 승인 후, 읽기 전용이라 상대적으로 가벼움)
4. D-004 (D-002 승인 후, D-003과 병행 가능하나 복잡도 높음 — D-003 이후 착수 권장)
5. D-005 (지금은 docs/06에 "Defer" 결정만 기록, 실제 도구 설계는 뒤로 미룸)

## Track 0 — S-001~S-011 재설계 (HANDOFF 기존 지시, 참고용)

이 문서가 새로 만드는 트랙 아님. HANDOFF.md에 이미 지시된 대로: RULEBOOK Backend #4-8/Agent workflow #6, ADR-0004/0005/0006, docs/02 pilot 섹션, docs/03 characterization/judge-verdict 섹션, pilot-selection-rubric을 design-only로 재검토. Track P/D와 파일 충돌 없음(다른 문서 영역) — 병행 가능.

## 전체 권장 실행 순서 (세 트랙 통합, 우선순위 = Critical 이슈 먼저)

1. P-001 (#11 Critical, 즉시 적용 가능)
2. Track 0 재설계 착수 (이미 지시된 작업, 이 문서와 무관하게 진행 가능)
3. P-002, P-003 설계 (병행) → 승인 대기
4. D-001 설계 → 승인 대기
5. (3 승인 후) P-004 설계 → 승인 대기 → (4 승인 후) D-002 ADR 작성 → 승인 대기
6. (5 승인 후) P-005 설계 → 승인 대기; D-002 승인 후 D-003 설계 → 승인 대기
7. P-006, P-007 설계 (P-002+P-005 승인 후) → 승인 대기; D-004 설계 (D-002+D-003 이후) → 승인 대기
8. P-008; D-005는 docs/06 Defer 기록만
9. P-009, P-010 — 언제든 병행 가능, 위 순서와 무관

## 마일스톤 — top-down vs bottom-up 판단 포함

세 트랙 전부 bottom-up(각자 세부구현 후 나중에 합침)으로 가면 안 되는 지점이 있음: Track D는 D-002(위험동작 가드)가 D-003/004/005의 연결 방식·프로필 이름·예외처리를 전부 결정하므로, 가드 없이 세 도구를 따로 만들면 나중에 전부 뜯어고쳐야 함(#20 원문: "모든 DB 쓰기 스크립트의 필수 진입점"). 이 지점만 top-down.

Track P는 P-002(STATE/QUEUE enum)·P-003(grade history 필드) 두 개만 먼저 고정하면 나머지(P-004~008)는 서로 자기 파일만 건드리는 leaf 작업이라 병렬 bottom-up 가능 — 합칠 필요 없음.

Track 0(S-001~11 재설계)은 기존 지시대로 별도 진행, 다른 두 트랙과 파일 안 겹쳐 전체 마일스톤과 항상 병행.

| 마일스톤 | 내용 | 방식 | 완료조건 |
|---|---|---|---|
| M0 | P-002·P-003·D-001 설계 확정 + P-001/P-009/P-010 즉시 실행 | top-down(P-002/003/D-001), 나머지 병행 | 사용자 승인 |
| M1 | P-004(enum검증기 설계), D-002 ADR(가드 아키텍처) | top-down(D-002 그림 먼저) | 사용자 승인 |
| M2 | P-005(feature 산출물 검증기 설계+구현), D-002 구현 | M1 승인 후 착수 | 구현 완료 + 리뷰 |
| M3 | P-006/P-007/P-008(agent/command/skill 전파, 병렬), D-003(MSSQL 조회), D-004(스냅샷/diff) | bottom-up — M0~M2가 정한 규약 위에서 병렬 | 개별 승인 |
| M4 | D-005는 docs/06 Defer 기록만, QUEUE.md에 전체 항목 등록(S-012 패턴) | 마무리 | 등록 완료 |

Track 0은 M0~M4 전체와 병행, 별도 승인 흐름으로 진행.

## 명시적 비고

- "설계게이트 필요" 항목은 각각 설계 산출물(RULEBOOK 조항/ADR/docs 갱신)만 만들고 **멈춘다**. 사용자가 해당 항목에 대해 명시적으로 "설계 끝났다, 구현 시작해라"라고 말하기 전까지 코드/스크립트를 작성하지 않는다(AGENTS.md #13).
- P-001/P-009/P-010은 프로즈 추가라 lock-in 낮음으로 판단했으나, 실제 착수 시 사용자가 다르게 판단하면 즉시 설계게이트로 전환한다.
- D-002는 이 계획에서 유일한 "상" lock-in 항목 — blast radius가 운영 DB 파괴이므로 다른 모든 DB 도구가 이 가드를 통과하도록 강제해야 한다는 이슈 원문 의견을 그대로 반영.
- 이 문서 승인 후 QUEUE.md에 P-/D- 항목을 등록하는 절차(S-012 패턴과 동일)는 아직 하지 않음 — 사용자 승인 후 별도 스텝으로 처리.
