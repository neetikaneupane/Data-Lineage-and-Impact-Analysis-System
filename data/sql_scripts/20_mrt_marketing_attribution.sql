CREATE TABLE mrt_marketing_attribution AS
WITH campaign_events AS (
    SELECT
        customer_id,
        campaign_id,
        COUNT(event_id)                 AS touch_count,
        MIN(occurred_at)                AS first_touch,
        MAX(occurred_at)                AS last_touch
    FROM raw_events
    WHERE campaign_id IS NOT NULL
    GROUP BY customer_id, campaign_id
)
SELECT
    ce.campaign_id,
    ce.customer_id,
    c.country,
    ce.touch_count,
    ce.first_touch,
    ce.last_touch,
    clv.total_spent
FROM campaign_events ce
LEFT JOIN dim_customers c
    ON ce.customer_id = c.customer_id
LEFT JOIN mrt_customer_lifetime_value clv
    ON ce.customer_id = clv.customer_id;