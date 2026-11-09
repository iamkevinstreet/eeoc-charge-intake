-- The export contract's rule on every field: an accepted field keeps
-- what the model read, and a rejected one ends empty.
select
    field_review_key,
    field,
    decision
from {{ ref('fct_field_reviews') }}
where
    (decision = 'accept' and changed)
    or (decision = 'reject' and reviewed_value is not null)
