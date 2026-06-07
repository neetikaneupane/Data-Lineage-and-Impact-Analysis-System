CREATE TABLE stg_customers AS
SELECT
    customer_id,
    LOWER(email)                        AS email,
    TRIM(full_name)                     AS full_name,
    phone,
    UPPER(country)                      AS country,
    created_at,
    updated_at
FROM raw_customers
WHERE email IS NOT NULL
  AND customer_id IS NOT NULL;