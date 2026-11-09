-- Grain: one row per charge: the latest review of it, and how many
-- reviews it had. Each live run reads the same documents again, so a
-- charge can be reviewed more than once; the latest record stands.
with ranked as (
    select
        *,
        row_number() over (
            partition by charge_key order by exported_at desc, review_id desc
        ) as recency,
        count(*) over (partition by charge_key) as reviews
    from {{ ref('int_reviews__records') }}
)

select
    charge_key,
    review_id,
    export_id,
    charge_number,
    charging_party,
    eeoc_office,
    earliest_date,
    latest_date,
    continuing_action,
    notice_date,
    response_due,
    source,
    exported_at,
    reviews
from ranked
where recency = 1
