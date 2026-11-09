-- A group's values as one sorted text, items joined by "|". dbt's own
-- listagg ignores its order on Spark and Databricks, so each adapter
-- gets the form it sorts with; an empty group is blank on both.
{% macro sorted_list(column) -%}
    {{ return(adapter.dispatch('sorted_list', 'eeoc_charge_intake')(column)) }}
{%- endmacro %}

{% macro default__sorted_list(column) -%}
    nullif(string_agg({{ column }}, '|' order by {{ column }}), '')
{%- endmacro %}

{% macro databricks__sorted_list(column) -%}
    nullif(array_join(array_sort(collect_list({{ column }})), '|'), '')
{%- endmacro %}
