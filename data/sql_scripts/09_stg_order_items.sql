CREATE TABLE stg_order_items AS
SELECT
    item_id,
    order_id,
    product_id,
    quantity,
    unit_price,
    COALESCE(discount, 0.00)            AS discount
FROM raw_order_items
WHERE item_id IS NOT NULL
  AND quantity > 0;