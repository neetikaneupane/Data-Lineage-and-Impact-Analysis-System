CREATE TABLE mrt_customer_lifetime_value AS
WITH order_totals AS (
    SELECT
        customer_id,
        COUNT(order_id)                 AS order_count,
        SUM(total_amount)               AS total_spent
    FROM fct_orders
    GROUP BY customer_id
),
payment_totals AS (
    SELECT
        customer_id,
        SUM(amount)                     AS total_paid
    FROM fct_payments
    GROUP BY customer_id
)
SELECT
    c.customer_id,
    c.full_name,
    c.country,
    c.customer_since,
    ot.order_count,
    ot.total_spent,
    pt.total_paid
FROM dim_customers c
LEFT JOIN order_totals ot
    ON c.customer_id = ot.customer_id
LEFT JOIN payment_totals pt
    ON c.customer_id = pt.customer_id;