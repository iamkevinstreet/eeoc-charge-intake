-- Grain: one row per review, its latest export's record with each single
-- value in a column of its own; the lists (respondents, bases, issues)
-- stay rows. A charge is known by its number, or by the document it came
-- from when the form leaves the number blank.
with latest as (
    select * from {{ ref('int_reviews__latest_exports') }}
),

record as (
    select
        v.export_id,
        max(case when v.field = 'charge_number' then v.value end) as charge_number,
        max(case when v.field = 'charging_party' then v.value end) as charging_party,
        max(case when v.field = 'eeoc_office' then v.value end) as eeoc_office,
        max(case when v.field = 'earliest_date' then v.value end) as earliest_date,
        max(case when v.field = 'latest_date' then v.value end) as latest_date,
        max(case when v.field = 'continuing_action' then v.value end) as continuing_action,
        max(case when v.field = 'notice_date' then v.value end) as notice_date
    from {{ ref('stg_reviews__export_values') }} as v
    inner join latest on latest.export_id = v.export_id
    where v.version = 'record'
    group by v.export_id
)

select
    latest.review_id,
    latest.export_id,
    coalesce(record.charge_number, latest.source) as charge_key,
    record.charge_number,
    record.charging_party,
    record.eeoc_office,
    try_cast(record.earliest_date as date) as earliest_date,
    try_cast(record.latest_date as date) as latest_date,
    record.continuing_action = 'true' as continuing_action,
    try_cast(record.notice_date as date) as notice_date,
    latest.response_due,
    latest.source,
    latest.demo,
    latest.started_at,
    latest.exported_at,
    latest.exports
from latest
left join record on record.export_id = latest.export_id
