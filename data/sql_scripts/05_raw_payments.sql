CREATE TABLE raw_payments (
    payment_id      VARCHAR(36),
    order_id        VARCHAR(36),
    method          VARCHAR(50),
    amount          NUMERIC(12,2),
    status          VARCHAR(50),
    paid_at         TIMESTAMP
);