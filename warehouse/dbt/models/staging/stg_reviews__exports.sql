-- Grain: one row per export of a finished review.
select
    export_id,
    review_id,
    contract,
    source,
    demo,
    cast(started_at as timestamp) as started_at,
    cast(exported_at as timestamp) as exported_at,
    cast(response_due as date) as response_due,
    file,
    cast(loaded_at as timestamp) as loaded_at
from {{ source('reviews', 'exports') }}
