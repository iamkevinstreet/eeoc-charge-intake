-- A surrogate key: the MD5 of the columns' values joined by "|", a
-- blank written as "~" so (a, null) and (null, a) stay apart. DuckDB,
-- Databricks and Snowflake all have md5 and concat_ws.
{% macro surrogate_key(columns) -%}
    md5(concat_ws('|'
    {%- for column in columns -%}
        , coalesce(cast({{ column }} as {{ dbt.type_string() }}), '~')
    {%- endfor -%}
    ))
{%- endmacro %}
