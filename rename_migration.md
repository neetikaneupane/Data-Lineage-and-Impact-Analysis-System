# Migration Checklist: Column Rename

| Field | Value |
|-------|-------|
| Source | `raw_customers.email` |
| Rename to | `email_address` |
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
  - Action: Rename reference 'email' → 'email_address' in 07_stg_customers.sql
  - Rollback: Revert 'email_address' → 'email' in 07_stg_customers.sql


### Depth 2

- **dim_customers.email** `[MEDIUM]`
  - Script: `12_dim_customers.sql`
  - Action: Rename reference 'email' → 'email_address' in 12_dim_customers.sql
  - Rollback: Revert 'email_address' → 'email' in 12_dim_customers.sql

- **fct_orders.customer_email** `[MEDIUM]` ⚠️ indirect break
  - Script: `14_fct_orders.sql`
  - Action: Rename reference 'email' → 'email_address' in 14_fct_orders.sql
  - Rollback: Revert 'email_address' → 'email' in 14_fct_orders.sql


### Depth 3

- **rpt_churn_risk.email** `[CRITICAL]`
  - Script: `22_rpt_churn_risk.sql`
  - Action: Rename reference 'email' → 'email_address' in 22_rpt_churn_risk.sql
  - Rollback: Revert 'email_address' → 'email' in 22_rpt_churn_risk.sql
