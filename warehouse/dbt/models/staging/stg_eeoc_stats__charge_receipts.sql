-- Grain: one row per basis or statute per fiscal year of Table E1a.
select
    table_id,
    basis,
    lower(basis) like 'total%' as is_total,
    cast(fiscal_year as bigint) as fiscal_year,
    cast(receipts as bigint) as receipts,
    source_url,
    source_sha256,
    cast(loaded_at as timestamp) as loaded_at
from {{ source('eeoc_stats', 'charge_receipts') }}
