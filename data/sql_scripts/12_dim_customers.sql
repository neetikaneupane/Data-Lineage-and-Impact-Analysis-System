CREATE TABLE dim_customers AS
SELECT
    c.customer_id,
    c.email,
    c.full_name,
    c.phone,
    c.country,
    c.created_at                        AS customer_since,
    COUNT(o.order_id)                   AS total_orders
FROM stg_customers c
LEFT JOIN stg_orders o
    ON c.customer_id = o.customer_id
GROUP BY
    c.customer_id,
    c.email,
    c.full_name,
    c.phone,
    c.country,
    c.created_at;