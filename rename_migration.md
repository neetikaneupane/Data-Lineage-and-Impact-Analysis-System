# Migration Checklist: Column Rename

**Source:** `raw_customers.email`  
**Rename to:** `email_address`  
**Total affected:** 4 downstream columns  

---

## Steps (ordered by dependency depth)


### Depth 1

- **stg_customers.email**
  - Script: `07_stg_customers.sql`
  - Action: Rename reference to 'email' → 'email_address' in 07_stg_customers.sql


### Depth 2

- **dim_customers.email**
  - Script: `12_dim_customers.sql`
  - Action: Rename reference to 'email' → 'email_address' in 12_dim_customers.sql

- **fct_orders.customer_email**
  - Script: `14_fct_orders.sql`
  - Action: Rename reference to 'email' → 'email_address' in 14_fct_orders.sql


### Depth 3

- **rpt_churn_risk.email**
  - Script: `22_rpt_churn_risk.sql`
  - Action: Rename reference to 'email' → 'email_address' in 22_rpt_churn_risk.sql
