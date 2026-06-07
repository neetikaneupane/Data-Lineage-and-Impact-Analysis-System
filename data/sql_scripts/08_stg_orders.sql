CREATE TABLE stg_orders AS
SELECT
    order_id,
    customer_id,
    LOWER(status)                       AS status,
    UPPER(currency)                     AS currency,
    total_amount,
    ordered_at,
    updated_at
FROM raw_orders
WHERE order_id IS NOT NULL
  AND customer_id IS NOT NULL;