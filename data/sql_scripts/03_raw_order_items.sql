CREATE TABLE raw_order_items (
    item_id         VARCHAR(36),
    order_id        VARCHAR(36),
    product_id      VARCHAR(36),
    quantity        INTEGER,
    unit_price      NUMERIC(12,2),
    discount        NUMERIC(5,2)
);