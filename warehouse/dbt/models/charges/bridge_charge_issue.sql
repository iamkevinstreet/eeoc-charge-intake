-- Grain: one row per charge and issue it raises.
select
    charge_key,
    {{ surrogate_key(['value']) }} as issue_key
from {{ ref('int_charges__list_values') }}
where field = 'issues'
