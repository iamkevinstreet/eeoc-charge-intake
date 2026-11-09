-- Grain: one row per export, version, field and list item.
select
    export_id,
    review_id,
    version,
    field,
    cast(position as bigint) as position,
    value
from {{ source('reviews', 'export_values') }}
