-- Grain: one row per charging party, known here only by a key and an
-- initial. The name stays in the raw table; on Databricks and Snowflake a
-- mask shows it to every reader, this build included, as its initial and
-- a fingerprint, which is all this needs to tell two people apart.
select distinct
    {{ surrogate_key(['lower(trim(charging_party))']) }} as charging_party_key,
    {{ dbt.concat(["upper(substring(trim(charging_party), 1, 1))", "'.'"]) }} as initial
from {{ ref('int_reviews__records') }}
where charging_party is not null
