-- Grain: one row per basis: the share of reviewed charges that cite it,
-- beside the share of the EEOC's charges that cited it in the latest
-- fiscal year the EEOC has published. A charge can cite more than one
-- basis, so neither share sums to one.
with charges as (
    select cast(count(*) as bigint) as charges from {{ ref('fct_charges') }}
),

cited as (
    select
        basis_key,
        cast(count(distinct charge_key) as bigint) as charges_citing
    from {{ ref('bridge_charge_basis') }}
    group by basis_key
),

latest_year as (
    select max(fiscal_year) as fiscal_year from {{ ref('fct_receipts_by_basis') }}
),

national as (
    select
        b.basis_key,
        r.basis as national_label,
        r.fiscal_year,
        r.receipts,
        r.share_of_charges
    from {{ ref('dim_basis') }} as b
    inner join {{ ref('fct_receipts_by_basis') }} as r
        on lower(r.basis) like lower(b.national_label_pattern)
    inner join latest_year as y on y.fiscal_year = r.fiscal_year
)

select
    b.basis_key,
    b.basis,
    coalesce(cited.charges_citing, 0) as reviewed_charges_citing,
    cast(coalesce(cited.charges_citing, 0) as double) / charges.charges as reviewed_share,
    national.national_label,
    national.fiscal_year as national_fiscal_year,
    national.receipts as national_receipts,
    national.share_of_charges as national_share,
    cast(coalesce(cited.charges_citing, 0) as double) / charges.charges
    - national.share_of_charges as share_difference
from {{ ref('dim_basis') }} as b
cross join charges
left join cited on cited.basis_key = b.basis_key
left join national on national.basis_key = b.basis_key
