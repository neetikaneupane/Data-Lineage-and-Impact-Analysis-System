CREATE TABLE raw_orders (
    order_id        VARCHAR(36),
    customer_id     VARCHAR(36),
    status          VARCHAR(50),
    currency        VARCHAR(10),
    total_amount    NUMERIC(12,2),
    ordered_at      TIMESTAMP,
    updated_at      TIMESTAMP
);
