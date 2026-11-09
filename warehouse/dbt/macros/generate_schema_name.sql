-- Names each schema exactly as its folder's config says (staging, a
-- mart's domain), in every target. dbt's default would prefix the target's
-- own schema; one warehouse per target makes the prefix unneeded.
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
