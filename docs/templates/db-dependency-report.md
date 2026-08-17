# DB Dependency Report: <database / schema scope>

- ID:
- Feature(s) affected:
- Status: draft | in-progress | reviewed | verified
- Source database / schema:
- Related open questions (docs/05-open-questions.md):

> 목적: RULEBOOK Database #2 — stored procedures, triggers, functions, views, jobs, constraints, defaults, collations, transaction behavior 인벤토리 채우기.
> 기입 원칙: 관찰된 사실과 추론을 분리하고, 모든 중요 항목에 Evidence grade(A/B/C/D/?)를 붙인다. grade를 묵묵히 상향하지 않는다.
> 운영 DB 원시 캡처는 Git 산출물이 아니다. 보고서에는 검토된 사실, 완전성 상태, 해시/근거 참조와 정책상 허용된 최소 인용만 남긴다.

## Inspection provenance and completeness

- Inspector / method:
- Inspector schema / revision:
- Capture ID:
- Captured at (UTC):
- Requested scope:
- Effective database / schema scope:
- Raw evidence reference (local/approved secure location; never credentials):
- Database catalog: COMPLETE | PARTIAL | BLOCKED | NOT-INSPECTED
- Module definitions: COMPLETE | PARTIAL | BLOCKED | NOT-INSPECTED
- SQL Server Agent jobs: NOT-REQUESTED | COMPLETE | PARTIAL | BLOCKED
- SQL Server Agent job-step text: NOT-REQUESTED | COMPLETE | PARTIAL | BLOCKED
- Completeness blockers / visibility limits:

A successful empty query is not an absence claim by itself. If metadata visibility, an unavailable/encrypted definition, `msdb` access, or a failed/unrun query prevents completeness, record it here and keep dependent conclusions unresolved.

## Unavailable / incomplete evidence

| Object / scope | Category | Status | Evidence / reason | Migration impact |
|---|---|---|---|---|
|  |  | UNAVAILABLE / NOT-INSPECTED / ERROR |  |  |

## Inventory summary

| 객체 유형 | 관측 개수 | 비즈니스 로직 포함 | 이전 대상 확정 | 정의/가시성 미확인 |
|---|---|---|---|---|
| Stored procedures |  |  |  |  |
| Triggers |  |  |  |  |
| Functions |  |  |  |  |
| Views |  |  |  |  |
| Jobs |  |  |  |  |
| Constraints |  |  |  |  |
| Defaults |  |  |  |  |
| Collations |  |  |  |  |
| Transaction patterns |  |  |  |  |

`관측 개수`는 위 completeness 상태가 `COMPLETE`가 아니면 전체 개수로 해석하지 않는다.

## Stored procedures

### SP-<n>: <이름>

- 목적 요약:
- 호출 주체 (앱 코드 / 다른 DB 객체 / job / 알 수 없음):
- Definition status: AVAILABLE | UNAVAILABLE | OMITTED_BY_POLICY | ERROR
- Definition hash / evidence ref:
- 비즈니스 로직 포함 여부: yes | no | unclear
- 포함된 로직 요약 (있는 경우):
- 이전 대상: FastAPI 서비스로 재구현 | PostgreSQL로 이전 | 의도적 보존 | 미정
- Evidence grade: A | B | C | D | ?
- 근거 (관찰/추론 구분):

## Triggers

### TRG-<n>: <이름>

- 목적 요약:
- 대상 테이블 / 이벤트 (INSERT/UPDATE/DELETE/기타):
- Definition status: AVAILABLE | UNAVAILABLE | OMITTED_BY_POLICY | ERROR
- Definition hash / evidence ref:
- 비즈니스 로직 포함 여부: yes | no | unclear
- 포함된 로직 요약 (있는 경우):
- 이전 대상: FastAPI 서비스로 재구현 | PostgreSQL로 이전 | 의도적 보존 | 미정
- Evidence grade: A | B | C | D | ?
- 근거 (관찰/추론 구분):

## Functions

### FN-<n>: <이름>

- 목적 요약:
- 유형 (scalar / table-valued / 기타):
- Definition status: AVAILABLE | UNAVAILABLE | OMITTED_BY_POLICY | ERROR
- Definition hash / evidence ref:
- 비즈니스 로직 포함 여부: yes | no | unclear
- 포함된 로직 요약 (있는 경우):
- 이전 대상: FastAPI 서비스로 재구현 | PostgreSQL로 이전 | 의도적 보존 | 미정
- Evidence grade: A | B | C | D | ?
- 근거 (관찰/추론 구분):

## Views

### VW-<n>: <이름>

- 목적 요약:
- 참조 테이블/객체:
- Definition status: AVAILABLE | UNAVAILABLE | OMITTED_BY_POLICY | ERROR
- Definition hash / evidence ref:
- 비즈니스 로직 포함 여부 (필터/변환/집계 등): yes | no | unclear
- 포함된 로직 요약 (있는 경우):
- 이전 대상: FastAPI 서비스로 재구현 | PostgreSQL로 이전 | 의도적 보존 | 미정
- Evidence grade: A | B | C | D | ?
- 근거 (관찰/추론 구분):

## Jobs

### JOB-<n>: <이름>

- 목적 요약:
- 스케줄 / 실행 조건:
- 호출하는 객체 (SP 등):
- Job-step text status: AVAILABLE | UNAVAILABLE | OMITTED_BY_POLICY | ERROR
- Job-step hash / evidence ref:
- 비즈니스 로직 포함 여부: yes | no | unclear
- 이전 대상: FastAPI 서비스로 재구현 | PostgreSQL로 이전 | 의도적 보존 | 미정
- Evidence grade: A | B | C | D | ?
- 근거 (관찰/추론 구분):

## Constraints

### CNT-<n>: <테이블.제약이름>

- 유형 (PK / FK / UNIQUE / CHECK / 기타):
- 목적 요약:
- 강제하는 무결성 규칙:
- Definition / expression status (해당 시): AVAILABLE | UNAVAILABLE | OMITTED_BY_POLICY | ERROR | N/A
- Definition hash / evidence ref:
- 비즈니스 로직 포함 여부: yes | no | unclear
- 이전 대상: FastAPI 서비스로 재구현 | PostgreSQL로 이전 | 의도적 보존 | 미정
- Evidence grade: A | B | C | D | ?
- 근거 (관찰/추론 구분):

## Defaults

### DFT-<n>: <테이블.컬럼>

- 기본값:
- Definition status: AVAILABLE | UNAVAILABLE | OMITTED_BY_POLICY | ERROR
- Definition hash / evidence ref:
- 목적 요약:
- 비즈니스 로직 포함 여부: yes | no | unclear
- 이전 대상: FastAPI 서비스로 재구현 | PostgreSQL로 이전 | 의도적 보존 | 미정
- Evidence grade: A | B | C | D | ?
- 근거 (관찰/추론 구분):

## Collations

### COL-<n>: <데이터베이스 / 컬럼 범위>

- 현재 collation:
- 목적 / 영향 (정렬, 비교, 대소문자 동작):
- PostgreSQL 이전 시 매핑 방침:
- Evidence grade: A | B | C | D | ?
- 근거 (관찰/추론 구분):

## Transaction behavior

### TXN-<n>: <패턴 이름>

- 위치 (앱 코드 / SP / trigger 내부):
- 범위와 격리 수준 (관찰된 경우):
- 롤백/커밋 조건과 side effects:
- 비즈니스 로직 포함 여부: yes | no | unclear
- 이전 대상: FastAPI 서비스로 재구현 | PostgreSQL로 이전 | 의도적 보존 | 미정
- Evidence grade: A | B | C | D | ?
- 근거 (관찰/추론 구분):

## Open questions

List every conclusion that remains blocked by `PARTIAL`/`BLOCKED` inspection coverage, unavailable definitions, or missing job visibility. Do not convert those cases to `no business logic` without independent evidence.

## Verification status
