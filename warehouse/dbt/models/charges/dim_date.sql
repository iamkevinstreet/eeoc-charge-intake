-- Grain: one row per day of the fiscal years the project's vars name,
-- with the federal fiscal year, October to September, that the EEOC's
-- statistics count by.
with days as (
    {{ dbt.date_spine(
        'day',
        "cast('" ~ var('date_spine_start') ~ "' as date)",
        "cast('" ~ var('date_spine_end') ~ "' as date)"
    ) }}
)

select
    cast(date_day as date) as date_day,
    cast(extract(year from date_day) as bigint) as calendar_year,
    cast(extract(month from date_day) as bigint) as calendar_month,
    cast(
        case
            when extract(month from date_day) >= 10 then extract(year from date_day) + 1
            else extract(year from date_day)
        end as bigint
    ) as fiscal_year
from days
