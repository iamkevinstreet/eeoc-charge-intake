-- The EEOC's own count of the charges it received each year, as its
-- reports published it, against the total the loaded Table E1a holds.
-- A row here means the table was misread, or the EEOC has revised the
-- year since its report.
with loaded as (
    select
        fiscal_year,
        receipts
    from {{ ref('stg_eeoc_stats__charge_receipts') }}
    where is_total
)

select
    p.fiscal_year,
    p.total_charges as published,
    loaded.receipts as loaded
from {{ ref('published_totals') }} as p
left join loaded on loaded.fiscal_year = p.fiscal_year
where loaded.receipts is null or loaded.receipts <> p.total_charges
