# Migration Checklist: Type Change

| Field | Value |
|-------|-------|
| Source | `raw_customers.email` |
| Type change | `VARCHAR` → `NUMERIC` |
| Risk level | HIGH |
| Risk note | string-to-number cast may fail on non-numeric values |
| Total affected columns | 4 |
| Scripts to update | 4 |

## Impact Summary by Layer

| Layer | Affected Columns | Scripts to Update |
|-------|-----------------|-------------------|
| dim | 1 | 1 |
| fct | 1 | 1 |
| rpt | 1 | 1 |
| stg | 1 | 1 |

## Safe Script Execution Order

1. `07_stg_customers.sql`
2. `12_dim_customers.sql`
3. `14_fct_orders.sql`
4. `22_rpt_churn_risk.sql`

## Steps (ordered by dependency depth)


### Depth 1

- **stg_customers.email** `[LOW]`
  - Script: `07_stg_customers.sql`
  - Action: Review 07_stg_customers.sql — string-to-number cast may fail on non-numeric values
  - Rollback: Revert type of email back to VARCHAR in 07_stg_customers.sql


### Depth 2

- **dim_customers.email** `[MEDIUM]`
  - Script: `12_dim_customers.sql`
  - Action: Review 12_dim_customers.sql — string-to-number cast may fail on non-numeric values
  - Rollback: Revert type of email back to VARCHAR in 12_dim_customers.sql

- **fct_orders.customer_email** `[MEDIUM]`
  - Script: `14_fct_orders.sql`
  - Action: Review 14_fct_orders.sql — string-to-number cast may fail on non-numeric values
  - Rollback: Revert type of email back to VARCHAR in 14_fct_orders.sql


### Depth 3

- **rpt_churn_risk.email** `[CRITICAL]`
  - Script: `22_rpt_churn_risk.sql`
  - Action: Review 22_rpt_churn_risk.sql — string-to-number cast may fail on non-numeric values
  - Rollback: Revert type of email back to VARCHAR in 22_rpt_churn_risk.sql
