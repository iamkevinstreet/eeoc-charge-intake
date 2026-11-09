-- Grain: one row per charge, as its latest review left it.
select
    charge_key,
    charge_number,
    review_id as latest_review_id,
    exported_at as reviewed_at,
    cast(reviews as bigint) as reviews,
    case
        when eeoc_office is not null then {{ surrogate_key(['eeoc_office']) }}
    end as office_key,
    case
        when charging_party is not null then {{ surrogate_key(['lower(trim(charging_party))']) }}
    end as charging_party_key,
    earliest_date,
    latest_date,
    cast({{ dbt.datediff('earliest_date', 'latest_date', 'day') }} as bigint) as days_of_harm,
    continuing_action,
    notice_date,
    response_due,
    source
from {{ ref('int_charges__latest_reviews') }}
