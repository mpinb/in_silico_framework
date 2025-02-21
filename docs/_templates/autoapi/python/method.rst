{% set root_module = obj.id.split('.')[0] | escape %}
{%- set breadcrumb = obj.id.split('.')[1:] %}
{% set shortname = obj.id.split('.')[-2:]|join('.')|escape %}

.. backlink:

{% if breadcrumb %}
:mod:`{{ root_module }}`
{%- for n in range(breadcrumb|length )  %}
 ❭ :mod:`~{{ root_module }}.{{ breadcrumb[:n+1] | join('.') }}`
{%- endfor %}
{% endif %}


{% if obj.display %}
   {% if is_own_page %}
{{ shortname }}
{{ "=" * shortname | length }}

   {% endif %}
.. py:method:: {{ obj.id }}({{ obj.args | replace("*", "\*") }}){% if obj.return_annotation is not none %} -> {{ obj.return_annotation }}{% endif %}
   {% for (args, return_annotation) in obj.overloads %}

               {%+ if is_own_page %}{{ obj.id }}{% else %}{{ obj.short_name }}{% endif %}({{ args | replace("*", "\*") }}){% if return_annotation is not none %} -> {{ return_annotation }}{% endif %}
   {% endfor %}
   {% for property in obj.properties %}

   :{{ property }}:
   {% endfor %}

   {% if obj.docstring %}

   {{ obj.docstring|indent(3) }}
   {% endif %}
{% endif %}
