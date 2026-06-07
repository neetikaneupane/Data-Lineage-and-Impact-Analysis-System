CREATE TABLE rpt_executive_summary AS
WITH revenue AS (
    SELECT
        SUM(gross_revenue)              AS total_gross_revenue,
        SUM(collected_revenue)          AS total_collected_revenue
    FROM mrt_daily_revenue
),
customers AS (
    SELECT
        COUNT(customer_id)              AS total_customers,
        AVG(total_spent)                AS avg_lifetime_value
    FROM mrt_customer_lifetime_value
),
products AS (
    SELECT
        SUM(revenue)                    AS total_product_revenue,
        SUM(gross_profit)               AS total_gross_profit
    FROM mrt_product_performance
)
SELECT
    r.total_gross_revenue,
    r.total_collected_revenue,
    c.total_customers,
    c.avg_lifetime_value,
    p.total_product_revenue,
    p.total_gross_profit
FROM revenue r
CROSS JOIN customers c
CROSS JOIN products p;