-- Grain: one row per export and field.
select
    export_id,
    review_id,
    field,
    decision,
    removed
from {{ source('reviews', 'export_decisions') }}
