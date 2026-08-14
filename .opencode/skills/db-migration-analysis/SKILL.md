---
name: db-migration-analysis
description: Use when analyzing MSSQL dependencies for a feature to identify data semantics and database-resident business logic before redesigning persistence for PostgreSQL.
compatibility: OpenCode project skill
---

# DB Migration Analysis

For the feature scope:

1. inventory tables/views/SPs/functions/triggers/jobs touched;
2. capture keys, constraints, defaults, precision, nullability, identity behavior, collations, and date/time semantics;
3. identify transaction/isolation expectations;
4. classify DB logic as integrity, business rule, query/reporting, or MSSQL-specific artifact;
5. map application assumptions around result ordering, row counts, concurrency, and errors;
6. identify data migration/compatibility risks;
7. propose PostgreSQL semantics only after the behavior is understood.

Do not mechanically translate T-SQL.
