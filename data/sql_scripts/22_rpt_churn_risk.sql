CREATE TABLE rpt_churn_risk AS
WITH last_order AS (
    SELECT
        customer_id,
        MAX(ordered_at)                 AS last_order_date,
        COUNT(order_id)                 AS total_orders
    FROM fct_orders
    GROUP BY customer_id
),
payment_health AS (
    SELECT
        customer_id,
        SUM(CASE WHEN payment_status = 'failed' THEN 1 ELSE 0 END)     AS failed_payments,
        SUM(CASE WHEN payment_status = 'completed' THEN 1 ELSE 0 END)  AS successful_payments
    FROM fct_payments
    GROUP BY customer_id
)
SELECT
    c.customer_id,
    c.full_name,
    c.email,
    c.country,
    lo.last_order_date,
    lo.total_orders,
    ph.failed_payments,
    ph.successful_payments,
    clv.total_spent
FROM dim_customers c
LEFT JOIN last_order lo
    ON c.customer_id = lo.customer_id
LEFT JOIN payment_health ph
    ON c.customer_id = ph.customer_id
LEFT JOIN mrt_customer_lifetime_value clv
    ON c.customer_id = clv.customer_id;