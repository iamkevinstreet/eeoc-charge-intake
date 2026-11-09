-- Grain: one row per protected basis a charge may cite, from the seed
-- that also names the label the EEOC's national statistics give it.
select
    {{ surrogate_key(['basis']) }} as basis_key,
    basis,
    national_label_pattern
from {{ ref('basis_map') }}
