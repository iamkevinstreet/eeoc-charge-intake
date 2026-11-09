-- Grain: one row per review and field, as the review's latest export
-- decided it: accepted as read, edited or rejected; whether the quote
-- check had emptied it before the reviewer saw it; and whether the
-- record ended different from what the model read. A field that names a
-- person shows no value here.
with latest as (
    select
        export_id,
        review_id,
        charge_key,
        exported_at
    from {{ ref('int_reviews__records') }}
),

texts as (
    select
        export_id,
        field,
        {{ sorted_list("case when version = 'record' then value end") }} as record_text,
        {{ sorted_list("case when version = 'extracted' then value end") }} as extracted_text
    from {{ ref('stg_reviews__export_values') }}
    group by export_id, field
)

select
    {{ surrogate_key(['d.review_id', 'd.field']) }} as field_review_key,
    d.review_id,
    latest.charge_key,
    d.field,
    d.decision,
    d.removed as emptied_by_quote_check,
    d.decision <> 'accept' as corrected,
    coalesce(t.record_text, '') <> coalesce(t.extracted_text, '') as changed,
    case
        when d.field not in ('{{ var("personal_fields") | join("', '") }}') then t.extracted_text
    end as extracted_value,
    case
        when d.field not in ('{{ var("personal_fields") | join("', '") }}') then t.record_text
    end as reviewed_value,
    latest.exported_at
from {{ ref('stg_reviews__export_decisions') }} as d
inner join latest on latest.export_id = d.export_id
left join texts as t on t.export_id = d.export_id and t.field = d.field
