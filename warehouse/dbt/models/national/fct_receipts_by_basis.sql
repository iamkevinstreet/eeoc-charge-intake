-- Grain: one row per basis or statute per fiscal year of the EEOC's
-- Table E1a: the charges citing it, their share of all charges that
-- year, and the change from the year before.
with receipts as (
    select * from {{ ref('stg_eeoc_stats__charge_receipts') }} where not is_total
),

totals as (
    select
        fiscal_year,
        receipts as total_charges
    from {{ ref('stg_eeoc_stats__charge_receipts') }}
    where is_total
)

select
    {{ surrogate_key(['r.basis', 'r.fiscal_year']) }} as receipt_key,
    r.basis,
    r.fiscal_year,
    r.receipts,
    t.total_charges,
    cast(r.receipts as double) / t.total_charges as share_of_charges,
    r.receipts - lag(r.receipts) over (
        partition by r.basis order by r.fiscal_year
    ) as change_from_prior_year,
    r.source_sha256
from receipts as r
left join totals as t on t.fiscal_year = r.fiscal_year
