CREATE TABLE fct_payments AS
SELECT
    p.payment_id,
    p.order_id,
    o.customer_id,
    p.method,
    p.amount,
    p.status                            AS payment_status,
    o.status                            AS order_status,
    p.paid_at
FROM stg_payments p
LEFT JOIN stg_orders o
    ON p.order_id = o.order_id;