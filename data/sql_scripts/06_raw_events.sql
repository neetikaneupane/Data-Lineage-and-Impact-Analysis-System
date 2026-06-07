CREATE TABLE raw_events (
    event_id        VARCHAR(36),
    customer_id     VARCHAR(36),
    event_type      VARCHAR(100),
    page            VARCHAR(255),
    campaign_id     VARCHAR(36),
    occurred_at     TIMESTAMP
);