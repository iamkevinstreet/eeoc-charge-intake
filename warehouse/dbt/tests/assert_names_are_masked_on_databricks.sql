-- On Databricks the build never reads a name: the column mask on the
-- raw values shows each value of a field that names a person as its
-- initial and a fingerprint (pipelines/masks.py). A row here is a name
-- the build could read. DuckDB has no masks, so the test runs on
-- Databricks alone.
{{ config(enabled=target.type == 'databricks') }}

select
    export_id,
    version,
    field
from {{ ref('stg_reviews__export_values') }}
where
    field in ('{{ var("personal_fields") | join("', '") }}')
    and not value rlike '^.[.] [0-9a-f]{12}$'
