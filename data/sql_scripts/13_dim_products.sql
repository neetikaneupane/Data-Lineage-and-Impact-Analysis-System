CREATE TABLE dim_products AS
SELECT
    p.product_id,
    p.product_name,
    p.category,
    p.unit_cost,
    p.created_at                        AS listed_at,
    COUNT(oi.item_id)                   AS times_ordered
FROM stg_products p
LEFT JOIN stg_order_items oi
    ON p.product_id = oi.product_id
GROUP BY
    p.product_id,
    p.product_name,
    p.category,
    p.unit_cost,
    p.created_at;