# Slices Draft — 레거시 접근 불필요, 즉시 실행 가능 작업

작성일: 2026-08-16
전제: 아래 slice는 전부 **확정된 결정**(AGENTS.md Target architecture defaults, docs/00 "Decisions made so far", ADR-0001~0003, RULEBOOK, docs/02~04/07의 확정 전략, OQ-024 CONFIRMED)에만 근거한다.

## 제외 기준 (요약)

- QUEUE Q-001~Q-005의 **실제 기입 작업**: OQ-001~013(OPEN) 의존 → 레거시 소스/DB/플랫폼 접근 필요.
- Q-006 파일럿 **실제 선정**: OQ-016 의존. (선정 **기준 정의**는 가능 → S-007)
- Host emulator / contract harness **구축**: docs/04 명시 "goal, not yet a confirmed possibility" + OQ-007/008 의존.
- 호환 C# DLL **결정/구현**: RULEBOOK Platform/DLL #3 (미해결) + OQ-009 의존.
- UI Inspector / 대형 오케스트레이터 / 외부 메모리: OQ-025~027 DEFERRED.
- 배포 토폴로지/인증/세션/시크릿 설계: OQ-018~021 의존.
- 이미 완료된 scaffold(agents/skills/commands/templates, docs, validate_scaffold.py, opencode.json plugin pin)는 제외.

## Slice 목록

| ID | Slice 이름 | 근거(문서:조항) | 난이도 | lock-in위험 | 이유 |
|---|---|---|---|---|---|
| S-001 | 검증 judge 프레임워크 스켈레톤 — contract test + DB assertion + snapshot + callback assertion + 수동 evidence를 결합하는 composite judge 구조 및 어댑터 인터페이스 | docs/03 §"Judge design under incomplete tests"(composite judge 구성 확정); ADR-0002(부수효과 중심 검증 채택); docs/00 Decisions #2 | 보통 | 중 | judge의 형태(증거 결합 방식, 결과 등급 PASS/FAIL/PARTIAL/BLOCKED)는 이후 모든 feature 검증의 기준이 되어 교체 비용이 큼. 단 구체 judge 연동 대상은 OQ-010 확정 후이므로 **프레임워크 뼈대+어댑터 포트까지만** |
| S-002 | Characterization 캡처 표준 스키마 — input fixture, 초기 DB 상태, 반환값, DB after, files, logs, callbacks, exception 항목을 포함한 기록 포맷(JSON/마크다운) 정의 및 저장 규칙 | docs/03 §"Characterization strategy"(8개 캡처 항목 확정); docs/00 Decisions #2, #3(golden-master 도입 결정) | 보통 | 중 | 캡처 포맷은 evidence 저장소·judge·재현 절차의 공통 호환 기반이라 초기 고정 후 변경 시 기존 evidence 재변환 비용 발생 |
| S-003 | 동치/정규화 비교 규칙 RULEBOOK 조항화 — 식별자·금액 exact, float 허용오차, 타임존/표기 정규화, 순서 무시 조건을 조항으로 명시 | docs/03 §"Equality rules"; RULEBOOK Evidence #5("normalization/tolerance는 명시적 문서화") | 간단 | 중 | 비교 규칙은 parity 판정의 준거가 되나 per-feature contract에서 재정의 가능하고 RULEBOOK 변경 절차(명시적 decision)가 있어 상 단계는 아님 |
| S-004 | DLL boundary report 템플릿 작성 — docs/04의 16개 분석 항목을 구조화 양식으로(docs/templates/에 추가) | docs/04 §"What the DLL analyzer must discover"(확정 체크리스트); QUEUE Q-001 완료 산출물 정의("DLL boundary report + OQ updates") | 간단 | 하 | 빈 양식만 만들고 기입은 레거시 접근 후. 양식 자체는 수정 자유로움 |
| S-005 | MSSQL DB 의존성 분석 리포트 템플릿 — SP/trigger/function/view/job/constraint/default/collation/transaction 인벤토리 양식 | RULEBOOK Database #2(인벤토리 항목 확정); QUEUE Q-005 산출물("DB dependency report") | 간단 | 하 | 빈 양식만. 기입은 OQ-013 확정 후 |
| S-006 | Pilot 선정 기준(rubric) 사전 정의 — 예: 부수효과 관찰 가능성, DB 로직 규모, DLL 경계 대표성, 폭발 반경 | docs/07 §Anthropic("use a pilot before broad conversion" 채택); ADR-0003(feature 단위 확정); docs/02 Phase 1→2 흐름; QUEUE Q-006 | 간단 | 하 | rubric은 실제 선정 시점(Q-004 완료 + OQ-016 확정 후)에 수정 가능한 사전 준비물. 실제 선정 작업은 제외됨 |
| S-007 | 대상 시스템 skeleton — monorepo(React/TS/Tailwind + FastAPI + PostgreSQL), docker-compose 로컬 dev, lint/test 설정, 구조 ADR 작성 | AGENTS.md §Target architecture defaults(스택 확정); docs/00 §Goal; docs/02 §Phase 0 게이트는 '광범위 구현'만 금지하므로 비즈니스 로직 없는 skeleton은 해당 없음 | 보통 | 중 | 디렉터리·빌드 구조는 코드가 쌓이기 전에 정해지면 이동 비용이 커짐. 단 비즈니스 로직을 담지 않으므로 상은 아님. 경계: feature 구현은 Phase 0 게이트 통과 전 금지 |
| S-008 | Platform adapter boundary 규약 — core가 platform/호환 모듈을 import하지 않는다는 의존성 규칙 + 포트 인터페이스 자리 + lint 가드 | RULEBOOK Platform/DLL #1~2("adapter boundary", core 직접 의존 금지); AGENTS.md #7; docs/04 §"Design rule" | 보통 | 상 | 아키텍처 경계는 코드 축적 후 변경 비용이 최대인 대표적 lock-in 결정. 호환 DLL 자체 채택(RULEBOOK #3, OQ-009)은 포함하지 않고 **규약과 가드만** |
| S-009 | FastAPI 요청/응답/오류 계약 컨벤션 — 표준 에러 모델, 계약 우선(endpoint=transport boundary) 규칙 문서화 + 공통 스키마 | RULEBOOK Backend #1~3("stable request/response/error contracts", "transport boundaries", "호환 로직 분리") | 간단 | 중 | API 계약 컨벤션은 초기 feature들이 따르게 되면 사실상 표준으로 굳어짐. S-007 이후 실행 |
| S-010 | 저장소 가드 자동화 — validate_scaffold.py 실행 자동화, OQ 상태 변경 시 evidence/source 기록 강제 검사, 문서 링크 검사 | ADR-0001 Consequences("project behavior remains visible in Git"); docs/05 §"Update rule"(상태 변경 절차 확정); README principle 6(disk-backed state) | 보통 | 하 | CI/검사 스크립트는 언제든 수정·제거 가능. OQ-024 pin 재현성 점검 포함 |
| S-011 | 파이프라인 dry-run — 합성(toy) feature로 discover→spec→design→implement→review→verify 전 단계를 실제 커맨드/에이전트/템플릿으로 순회하고, judge에 고의 오류를 주입해 FAIL을 감지하는지 확인(mutation self-test), 결과로 Rulebook/스킬 개선 도출 | docs/02 §Phase 0("make the process runnable before migrating production behavior" + judge 결정 output); docs/03 §"Judge design"(고의 오류 주입 규칙 확정); README principle 7(fix the process) | 복잡 | 하 | 산출물 자체는 폐기 가능한 합성 예제. 목적이 프로세스 조기 결함 발견이므로 되돌림 비용은 낮고, 발견 결함은 RULEBOOK/스킬 개선(RULEBOOK Agent workflow #5)으로 연결 |
| S-012 | 본 초안 확정 후 QUEUE.md/STATE.md 반영 — 승인된 slice를 Q-항목으로 등록 | README principle 6 / AGENTS.md #12(디스크 기반 queue로 resume 보장); migration/QUEUE.md 헤더 규칙(재개 가능 + 산출물 명시) | 간단 | 하 | 상태 파일 갱신은 가역적. 단 이 문서 승인(사람 게이트) 후 실행 |

## 권장 실행 순서

1. **문서/양식군(즉시, 병렬 가능)**: S-003 → S-004, S-005, S-006
2. **검증 기반군**: S-002 → S-001 (S-001은 S-002 스키마 사용)
3. **대상 구조군**: S-007 → S-008 → S-009
4. **프로세스 검증**: S-010 → S-011 (S-011은 1~3 산출물을 모두 소비하는 통합 dry-run)
5. **마무리**: S-012 (본 초안 승인 직후에도 선행 등록 가능)

## 명시적 비고

- S-001/S-002/S-011은 OQ-010(관찰 가능 출력 목록)과 무관하게 docs/03이 확정한 증거 유형 **전체**를 지원하는 구조만 만든다. 실제 legacy judge 선점(what acts as the judge)은 OQ-010 확정 후 별도 작업.
- S-007은 Phase 0 게이트(docs/02)를 위반하지 않도록 비즈니스 기능 구현을 포함하지 않는다. 게이트 통과 판단은 migration/STATE.md의 Next gate 항목 해소 시까지 유보.
- 모든 slice의 산출물은 기존 확정 아티팩트 형식(features/, evidence/, docs/templates/, RULEBOOK)을 따른다.
