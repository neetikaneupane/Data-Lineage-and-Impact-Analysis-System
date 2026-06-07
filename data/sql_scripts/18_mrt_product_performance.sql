CREATE TABLE mrt_product_performance AS
WITH item_stats AS (
    SELECT
        product_id,
        SUM(quantity)                   AS units_sold,
        SUM(line_total)                 AS revenue
    FROM fct_order_items
    GROUP BY product_id
)
SELECT
    p.product_id,
    p.product_name,
    p.category,
    p.unit_cost,
    i.units_sold,
    i.revenue,
    i.revenue - (p.unit_cost * i.units_sold)    AS gross_profit
FROM dim_products p
LEFT JOIN item_stats i
    ON p.product_id = i.product_id;