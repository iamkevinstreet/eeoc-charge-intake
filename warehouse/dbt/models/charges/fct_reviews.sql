-- Grain: one row per review, as its latest export left it: the charge
-- it was of, and how its fields were decided.
with decisions as (
    select
        export_id,
        cast(count(*) as bigint) as fields,
        cast(sum(case when decision = 'accept' then 1 else 0 end) as bigint) as accepted,
        cast(sum(case when decision = 'edit' then 1 else 0 end) as bigint) as edited,
        cast(sum(case when decision = 'reject' then 1 else 0 end) as bigint) as rejected,
        cast(sum(case when removed then 1 else 0 end) as bigint) as emptied_by_quote_check
    from {{ ref('stg_reviews__export_decisions') }}
    group by export_id
)

select
    r.review_id,
    r.export_id,
    r.charge_key,
    r.source,
    r.demo,
    r.started_at,
    r.exported_at,
    cast(r.exports as bigint) as exports,
    d.fields,
    d.accepted,
    d.edited,
    d.rejected,
    d.emptied_by_quote_check,
    d.edited + d.rejected = 0 as accepted_as_read
from {{ ref('int_reviews__records') }} as r
inner join decisions as d on d.export_id = r.export_id
