-- Grain: one row per charge, list field and item, from the charge's
-- latest review: the respondents it names, the bases it cites and the
-- issues it raises.
select
    c.charge_key,
    v.field,
    v.position,
    v.value
from {{ ref('int_charges__latest_reviews') }} as c
inner join {{ ref('stg_reviews__export_values') }} as v on v.export_id = c.export_id
where v.version = 'record' and v.field in ('respondent', 'bases', 'issues')
