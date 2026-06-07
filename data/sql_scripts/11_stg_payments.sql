CREATE TABLE stg_payments AS
SELECT
    payment_id,
    order_id,
    LOWER(method)                       AS method,
    amount,
    LOWER(status)                       AS status,
    paid_at
FROM raw_payments
WHERE payment_id IS NOT NULL
  AND amount > 0;