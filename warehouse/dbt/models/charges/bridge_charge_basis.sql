-- Grain: one row per charge and protected basis it cites.
select
    charge_key,
    {{ surrogate_key(['value']) }} as basis_key
from {{ ref('int_charges__list_values') }}
where field = 'bases'
