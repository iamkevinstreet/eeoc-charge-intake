-- Grain: one row per respondent per spelling of its name, type 2. A
-- respondent is known by its name in lower case and trimmed; a version
-- begins with the first export that recorded a spelling, and ends when
-- a later export records another.
with named as (
    select distinct
        {{ surrogate_key(['lower(trim(v.value))']) }} as respondent_key,
        trim(v.value) as respondent_name,
        e.exported_at
    from {{ ref('stg_reviews__export_values') }} as v
    inner join {{ ref('int_reviews__latest_exports') }} as e on e.export_id = v.export_id
    where v.version = 'record' and v.field = 'respondent'
),

changes as (
    select
        respondent_key,
        respondent_name,
        exported_at,
        lag(respondent_name) over (
            partition by respondent_key order by exported_at, respondent_name
        ) as previous_name
    from named
),

versions as (
    select
        respondent_key,
        respondent_name,
        exported_at as valid_from
    from changes
    where previous_name is null or previous_name <> respondent_name
)

select
    {{ surrogate_key(['respondent_key', 'valid_from']) }} as respondent_version_key,
    respondent_key,
    respondent_name,
    valid_from,
    lead(valid_from) over (partition by respondent_key order by valid_from) as valid_to,
    lead(valid_from) over (partition by respondent_key order by valid_from) is null as is_current
from versions
