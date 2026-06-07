CREATE TABLE fct_order_items AS
SELECT
    oi.item_id,
    oi.order_id,
    oi.product_id,
    o.customer_id,
    oi.quantity,
    oi.unit_price,
    oi.discount,
    (oi.quantity * oi.unit_price) - oi.discount    AS line_total,
    p.category                                      AS product_category
FROM stg_order_items oi
LEFT JOIN stg_orders o
    ON oi.order_id = o.order_id
LEFT JOIN stg_products p
    ON oi.product_id = p.product_id;