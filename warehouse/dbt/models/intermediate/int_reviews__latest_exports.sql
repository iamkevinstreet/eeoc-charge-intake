-- Grain: one row per review: its latest export. A review exported again
-- after a change has more than one, and the latest holds the record that
-- stands.
with ranked as (
    select
        export_id,
        review_id,
        source,
        demo,
        started_at,
        exported_at,
        response_due,
        row_number() over (
            partition by review_id order by exported_at desc, export_id desc
        ) as recency,
        count(*) over (partition by review_id) as exports
    from {{ ref('stg_reviews__exports') }}
)

select
    export_id,
    review_id,
    source,
    demo,
    started_at,
    exported_at,
    response_due,
    exports
from ranked
where recency = 1
