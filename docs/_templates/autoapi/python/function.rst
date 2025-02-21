{% set root_module = obj.id.split('.')[0] | escape %}
{%- set breadcrumb = obj.id.split('.')[1:] %}
{% set shortname = obj.name.split('.')[-1] | escape %}

.. backlink:

{% if breadcrumb %}
:mod:`{{ root_module }}`
{%- for n in range(breadcrumb|length )  %}
 ❭ :mod:`~{{ root_module }}.{{ breadcrumb[:n+1] | join('.') }}`
{%- endfor %}
{% endif %}


{% if obj.display %}
   {% if is_own_page %}

.. title:

{{ shortname }}
{{ "=" * shortname|length }}

   {% endif %}

.. py:function:: {{ obj.id }}({{ obj.args | e }}){% if obj.return_annotation is not none %} -> {{ obj.return_annotation }}{% endif %}
   {% for (args, return_annotation) in obj.overloads %}

                 {%+ if is_own_page %}{{ obj.id }}{% else %}{{ obj.short_name }}{% endif %}({{ args | e }}){% if return_annotation is not none %} -> {{ return_annotation }}{% endif %}
   {% endfor %}
   {% for property in obj.properties %}

   :{{ property }}:
   {% endfor %}

   {% if obj.docstring %}

   {{ obj.docstring | replace("_", "\_") | indent(3) }}
   {% endif %}
{% endif %}

.. 
   Warning: we replace underscores with an escape backslash about 4 lines above to avoid having Sphinx interpret arguments as links.
   However, this may cause issues with code blocks or other literal text, and malform markdown tables
   Use with caution?
..
