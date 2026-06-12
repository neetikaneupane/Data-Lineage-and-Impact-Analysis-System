# Migration Checklist: Type Change

**Source:** `raw_customers.email`  
**Type change:** `VARCHAR` → `NUMERIC`  
**Risk:** string-to-number cast may fail on non-numeric values  
**Total affected:** 4 downstream columns  

---

## Steps (ordered by dependency depth)


### Depth 1

- **stg_customers.email**
  - Script: `07_stg_customers.sql`
  - Action: Review 07_stg_customers.sql — string-to-number cast may fail on non-numeric values


### Depth 2

- **dim_customers.email**
  - Script: `12_dim_customers.sql`
  - Action: Review 12_dim_customers.sql — string-to-number cast may fail on non-numeric values

- **fct_orders.customer_email**
  - Script: `14_fct_orders.sql`
  - Action: Review 14_fct_orders.sql — string-to-number cast may fail on non-numeric values


### Depth 3

- **rpt_churn_risk.email**
  - Script: `22_rpt_churn_risk.sql`
  - Action: Review 22_rpt_churn_risk.sql — string-to-number cast may fail on non-numeric values
