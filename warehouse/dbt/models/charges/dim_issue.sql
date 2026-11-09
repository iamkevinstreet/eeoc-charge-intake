-- Grain: one row per issue a reviewed charge raises.
select distinct
    {{ surrogate_key(['value']) }} as issue_key,
    value as issue
from {{ ref('int_charges__list_values') }}
where field = 'issues'
