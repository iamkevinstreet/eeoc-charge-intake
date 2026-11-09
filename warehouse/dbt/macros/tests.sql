-- Generic tests the marts share, so no package is needed.

-- Fails for each set of the columns' values that appears twice.
{% test unique_combination(model, columns) %}
    select {{ columns | join(', ') }}, count(*) as copies
    from {{ model }}
    group by {{ columns | join(', ') }}
    having count(*) > 1
{% endtest %}

-- Fails for each value outside [min_value, max_value]; blanks pass.
{% test between(model, column_name, min_value, max_value) %}
    select {{ column_name }}
    from {{ model }}
    where {{ column_name }} < {{ min_value }} or {{ column_name }} > {{ max_value }}
{% endtest %}
