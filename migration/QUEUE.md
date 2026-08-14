# Migration Queue

Queue items must be small enough to resume from disk and have an observable completion artifact.

| ID | Status | Phase | Work item | Completion artifact |
|---|---|---|---|---|
| Q-001 | TODO | 0 | Inspect DLL public surface and host integration | DLL boundary report + OQ updates |
| Q-002 | TODO | 0 | Inventory existing tests/CI | test inventory + evidence assessment |
| Q-003 | TODO | 0 | Identify observable outputs available outside UI | judge capability matrix |
| Q-004 | TODO | 1 | Generate legacy feature inventory | feature cards in `migration/features/` |
| Q-005 | TODO | 1 | Map MSSQL business logic objects | DB dependency report |
| Q-006 | TODO | 2 | Select one pilot feature | approved pilot feature card |
| Q-007 | BLOCKED | 2 | Build pilot behavior contract | blocked by Q-004/Q-006 |
| Q-008 | BLOCKED | 3 | Design pilot target slice | blocked by Q-007 |
| Q-009 | BLOCKED | 4 | Implement pilot | blocked by Q-008 |
| Q-010 | BLOCKED | 5-6 | Independent review + verification | blocked by Q-009 |
