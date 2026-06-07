CREATE TABLE raw_customers (
    customer_id     VARCHAR(36),
    email           VARCHAR(255),
    full_name       VARCHAR(255),
    phone           VARCHAR(50),
    country         VARCHAR(100),
    created_at      TIMESTAMP,
    updated_at      TIMESTAMP
);