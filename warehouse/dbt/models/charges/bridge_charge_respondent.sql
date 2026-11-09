-- Grain: one row per charge and respondent it names; the first named is
-- the employer the notice of charge went to.
select
    charge_key,
    {{ surrogate_key(['lower(trim(value))']) }} as respondent_key,
    position,
    position = 0 as is_first_named
from {{ ref('int_charges__list_values') }}
where field = 'respondent'
