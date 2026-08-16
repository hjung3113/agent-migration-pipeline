# DB Dependency Report: <database / schema scope>

- ID:
- Feature(s) affected:
- Status: draft | in-progress | reviewed | verified
- Source database / schema:
- Related open questions (docs/05-open-questions.md):

> 목적: RULEBOOK Database #2 — stored procedures, triggers, functions, views, jobs, constraints, defaults, collations, transaction behavior 인벤토리 채우기.
> 기입 원칙: 관찰된 사실과 추론을 분리하고, 모든 중요 항목에 Evidence grade(A/B/C/D/?)를 붙인다. grade를 묵묵히 상향하지 않는다.

## Inventory summary

| 객체 유형 | 총 개수 | 비즈니스 로직 포함 | 이전 대상 확정 | 미확인 |
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

## Stored procedures

### SP-<n>: <이름>

- 목적 요약:
- 호출 주체 (앱 코드 / 다른 DB 객체 / job / 알 수 없음):
- 비즈니스 로직 포함 여부: yes | no | unclear
- 포함된 로직 요약 (있는 경우):
- 이전 대상: FastAPI 서비스로 재구현 | PostgreSQL로 이전 | 의도적 보존 | 미정
- Evidence grade: A | B | C | D | ?
- 근거 (관찰/추론 구분):

## Triggers

### TRG-<n>: <이름>

- 목적 요약:
- 대상 테이블 / 이벤트 (INSERT/UPDATE/DELETE):
- 비즈니스 로직 포함 여부: yes | no | unclear
- 포함된 로직 요약 (있는 경우):
- 이전 대상: FastAPI 서비스로 재구현 | PostgreSQL로 이전 | 의도적 보존 | 미정
- Evidence grade: A | B | C | D | ?
- 근거 (관찰/추론 구분):

## Functions

### FN-<n>: <이름>

- 목적 요약:
- 유형 (scalar / table-valued / 기타):
- 비즈니스 로직 포함 여부: yes | no | unclear
- 포함된 로직 요약 (있는 경우):
- 이전 대상: FastAPI 서비스로 재구현 | PostgreSQL로 이전 | 의도적 보존 | 미정
- Evidence grade: A | B | C | D | ?
- 근거 (관찰/추론 구분):

## Views

### VW-<n>: <이름>

- 목적 요약:
- 참조 테이블/객체:
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
- 비즈니스 로직 포함 여부: yes | no | unclear
- 이전 대상: FastAPI 서비스로 재구현 | PostgreSQL로 이전 | 의도적 보존 | 미정
- Evidence grade: A | B | C | D | ?
- 근거 (관찰/추론 구분):

## Constraints

### CNT-<n>: <테이블.제약이름>

- 유형 (PK / FK / UNIQUE / CHECK / 기타):
- 목적 요약:
- 강제하는 무결성 규칙:
- 비즈니스 로직 포함 여부: yes | no | unclear
- 이전 대상: FastAPI 서비스로 재구현 | PostgreSQL로 이전 | 의도적 보존 | 미정
- Evidence grade: A | B | C | D | ?
- 근거 (관찰/추론 구분):

## Defaults

### DFT-<n>: <테이블.컬럼>

- 기본값:
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

## Verification status
