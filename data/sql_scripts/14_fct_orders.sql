CREATE TABLE fct_orders AS
SELECT
    o.order_id,
    o.customer_id,
    o.status,
    o.currency,
    o.total_amount,
    o.ordered_at,
    c.country                           AS customer_country,
    c.email                             AS customer_email
FROM stg_orders o
LEFT JOIN stg_customers c
    ON o.customer_id = c.customer_id;