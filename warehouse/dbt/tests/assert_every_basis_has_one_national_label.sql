-- Every basis a charge may cite matches exactly one label of Table E1a
-- in the latest fiscal year loaded, so the comparison with the national
-- figures never drops a basis or counts one twice.
with latest as (
    select max(fiscal_year) as fiscal_year from {{ ref('fct_receipts_by_basis') }}
),

matches as (
    select
        b.basis,
        count(r.basis) as labels
    from {{ ref('dim_basis') }} as b
    cross join latest
    left join {{ ref('fct_receipts_by_basis') }} as r
        on lower(r.basis) like lower(b.national_label_pattern)
        and r.fiscal_year = latest.fiscal_year
    group by b.basis
)

select
    basis,
    labels
from matches
where labels <> 1
