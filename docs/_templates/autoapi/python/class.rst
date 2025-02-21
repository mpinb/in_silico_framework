{% import 'macros.rst' as macros %}
{% set root_module = obj.id.split('.')[0] | escape %}
{%- set breadcrumb = obj.id.split('.')[1:] %}

{% if obj.display %}
   {% if is_own_page %}

.. breadcrumb trail -----------------------------------------------------------------------

      {% if breadcrumb %}
:mod:`{{ root_module }}`
         {%- for n in range(breadcrumb|length )  %}
 ❭ :mod:`~{{ root_module }}.{{ breadcrumb[:n+1] | join('.') }}`
         {%- endfor %}

      {% endif %}

.. main page title: MUST be BEFORE toctree trigger -------------------------------

{{ obj.short_name }}
{{ "=" * obj.short_name | length }}
   {% endif %}

.. setup: which children to show -------------------------------------------------

   {% set visible_children = obj.children | selectattr("display") | list %}
   {% set own_page_children = visible_children | selectattr("type", "in", own_page_types) | list %}
   {% if own_page_children %}
      {% set visible_methods = own_page_children | selectattr("type", "equalto", "method") | list %}
      {% set visible_attributes = own_page_children | selectattr("type", "equalto", "attribute") | list %}

.. Trigger the toctree structure in the sidebar for this page

.. toctree::
   :hidden:

      {% for method in visible_methods %}
   {{ method.short_name }} <{{ obj.short_name }}.{{ method.short_name }}>
      {% endfor %}

   {% endif %}

.. parse out arguments and attributes from class, __init__ & __new__ docstring --------------------

   {%- if obj.docstring %}
      {%- set docstring_lines = obj.docstring.split('\n') %}      
      {%- set first_attribute_line_index = docstring_lines | find_first_match('.. attribute::') %}

.. fetch attributes and docstring from class docstring

      {%- if first_attribute_line_index != -1   %}
         {%- set pure_docstring_lines = docstring_lines[:first_attribute_line_index] %}
         {%- set attribute_lines = docstring_lines[first_attribute_line_index:] %}
      {%- else %}
         {%- set pure_docstring_lines = docstring_lines %}
         {%- set attribute_lines = [] %}
      {%- endif %}

.. fetch arguments from __init__ or __new__ docstring

      {%- set init_docstring = obj.children | selectattr("name", "equalto", "__init__") | map(attribute="docstring") | list  %}
      {%- set new_docstring = obj.children | selectattr("name", "equalto", "__new__") | map(attribute="docstring") | list %}
      {%- set argument_lines = [] %}
      {%- if init_docstring %}
         {%- set argument_lines = init_docstring %}
      {%- elif new_docstring %}
         {%- set argument_lines = new_docstring %}
      {%- endif %}
      {%- set argument_lines = argument_lines | reject("==", '') | reject("==", "\n") | list %}
      {%- if argument_lines == [''] %}
         {%- set argument_lines = [] %}
      {%- endif %}

   {% endif %}

.. class signature --------------------------------------------------------------

.. py:class:: {{ obj.id }}{% if obj.args %}({{ obj.args }}){% endif %}
   
   {%- for (args, return_annotation) in obj.overloads %}
      {{ " " * (obj.type | length) }}   {{ obj.short_name }}{% if args %}({{ args }}){% endif %}
   {%- endfor %}
   {%- if obj.bases %}
      {% if "show-inheritance" in autoapi_options %}

   Bases: {% for base in obj.bases %}{{ base|link_objs }}{% if not loop.last %}, {% endif %}{% endfor %}
      {% endif %}
   {% endif %}

   {% if pure_docstring_lines %}
   
   {{ pure_docstring_lines | join('\n') | indent(3) }}
   
   {%- endif %}
   {%- if argument_lines %}

   {{ argument_lines | join('\n') | indent(3) }}
      
   {%- endif %}
   {%- if attribute_lines %}

   .. rst-class:: class-header

   .. py:data:: Attributes

   
   {{ attribute_lines | join('\n') | indent(3) }}
   

   {%- endif %}

   {%- if visible_methods %}

   
   .. rst-class:: class-header

   .. py:data:: Methods

   {{ macros.auto_summary(visible_methods) | indent(3) }}

{%- endif %}

{% endif %}
