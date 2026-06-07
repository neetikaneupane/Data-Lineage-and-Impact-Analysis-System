CREATE TABLE mrt_daily_revenue AS
WITH daily_orders AS (
    SELECT
        DATE(ordered_at)                AS order_date,
        currency,
        COUNT(order_id)                 AS order_count,
        SUM(total_amount)               AS gross_revenue
    FROM fct_orders
    GROUP BY DATE(ordered_at), currency
),
daily_payments AS (
    SELECT
        DATE(paid_at)                   AS payment_date,
        SUM(amount)                     AS collected_revenue
    FROM fct_payments
    WHERE payment_status = 'completed'
    GROUP BY DATE(paid_at)
)
SELECT
    d.order_date,
    d.currency,
    d.order_count,
    d.gross_revenue,
    p.collected_revenue
FROM daily_orders d
LEFT JOIN daily_payments p
    ON d.order_date = p.payment_date;