CREATE TABLE stg_products AS
SELECT
    product_id,
    TRIM(product_name)                  AS product_name,
    LOWER(category)                     AS category,
    unit_cost,
    created_at
FROM raw_products
WHERE product_id IS NOT NULL
  AND unit_cost > 0;