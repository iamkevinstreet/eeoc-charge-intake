-- Grain: one row per EEOC office a reviewed charge names.
select distinct
    {{ surrogate_key(['eeoc_office']) }} as office_key,
    eeoc_office as office
from {{ ref('int_reviews__records') }}
where eeoc_office is not null
