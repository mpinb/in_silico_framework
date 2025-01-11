{% import 'macros.rst' as macros %}
{% set root_module = obj.id.split('.')[0] | escape %}
{%- set breadcrumb = obj.id.split('.')[1:] %}

.. Note that class attributes are rendered within the docstring, as taken care of by Napoleon. They do not need a separate section.

{% if obj.display %}
   {% if is_own_page %}

.. backlink:

{% if breadcrumb %}
:mod:`{{ root_module }}`
{%- for n in range(breadcrumb|length )  %}
 ❭ :mod:`~{{ root_module }}.{{ breadcrumb[:n+1] | join('.') }}`
{%- endfor %}
{% endif %}


{{ obj.short_name }}
{{ "=" * obj.short_name | length }}

   {% endif %}

{% set visible_children = obj.children|selectattr("display")|list %}
{% set own_page_children = visible_children|selectattr("type", "in", own_page_types)|list %}
   {% if own_page_children %}
{% set visible_methods = own_page_children|selectattr("type", "equalto", "method")|list %}
{% set visible_attributes = own_page_children|selectattr("type", "equalto", "attribute")|list %}

.. toctree::
   :hidden:

   {% for method in visible_methods %}
   {{ method.short_name }} <{{ obj.short_name }}.{{ method.short_name }}>
   {% endfor %}

   {% endif %}

.. py:class:: {{ obj.id }}{% if obj.args %}({{ obj.args }}){% endif %}

   
   {% for (args, return_annotation) in obj.overloads %}
      {{ " " * (obj.type | length) }}   {{ obj.short_name }}{% if args %}({{ args }}){% endif %}
   {% endfor %}
   {% if obj.bases %}
      {% if "show-inheritance" in autoapi_options %}

   Bases: {% for base in obj.bases %}{{ base|link_objs }}{% if not loop.last %}, {% endif %}{% endfor %}
      {% endif %}
   {% endif %}

   {%- if obj.docstring %}
   {{ obj.docstring|indent(3) }}
   {% endif %}

   {%- if visible_methods %}
   {%- set public_methods = visible_methods|rejectattr('is_private_member')|list %}
   {%- if public_methods %}
{{ macros.auto_summary(public_methods, title="Methods") }}
   {%- endif %}
   {%- endif %}
   {%- endif %}
