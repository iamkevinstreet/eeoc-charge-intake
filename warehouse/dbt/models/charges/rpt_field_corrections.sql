-- Grain: one row per field per review, in the order the reviews were
-- exported: how often a reviewer has had to correct the field so far,
-- across every review up to and including this one.
with ordered as (
    select
        field,
        review_id,
        exported_at,
        corrected,
        cast(sum(case when corrected then 1 else 0 end) over (
            partition by field order by exported_at, review_id
            rows between unbounded preceding and current row
        ) as bigint) as corrections_so_far,
        cast(row_number() over (
            partition by field order by exported_at, review_id
        ) as bigint) as reviews_so_far
    from {{ ref('fct_field_reviews') }}
)

select
    {{ surrogate_key(['field', 'review_id']) }} as correction_key,
    field,
    review_id,
    exported_at,
    corrected,
    corrections_so_far,
    reviews_so_far,
    cast(corrections_so_far as double) / reviews_so_far as correction_rate_so_far
from ordered
