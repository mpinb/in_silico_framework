.. adapted from https://bylr.info/articles/2022/05/10/api-doc-with-sphinx-autoapi/#basic-macro-setup

.. 
  Note that the object args are of type e.g.: ArgInfo(prefix=None, name='cell', annotation=None, default_value='None')
  So arg[0] is the prefix (e.g. asterisks for *args and **kwargs), and arg[1] is the argument name
..

{% macro _render_item_name(obj, sig=False) -%} :py:obj:`{{ obj.name.split('.')[-1] }} <{{ obj.id }}>`
     {%- if sig -%}
       \ (
       {%- for arg in obj.obj.args -%}
          {%- if arg[0] %}{{ arg[0] | replace('*', '\*') }}{% endif -%}{{  arg[1] | replace("_", "\_") -}}
          {%- if not loop.last  %}, {% endif -%}
       {%- endfor -%}
       ){%- endif -%}
{%- endmacro %}

{% macro _item(obj, sig=False, label='') %}
   * - {{ _render_item_name(obj, sig) }}
     - {% if label %}:summarylabel:`{{ label }}` {% endif %}{% if obj.summary %}{{ obj.summary }}{% else %}\-{% endif +%}
{% endmacro %}

{% macro auto_summary(objs, title='', table_title='') -%}
{% if title %}

.. rst-class:: absolute-paragraph

{{ title }}
{{ '-' * title|length }}

{% endif %}

.. list-table:: {{ table_title }}
   :header-rows: 0
   :widths: auto
   :class: summarytable
   
   {% for obj in objs -%}
       {%- set sig = (obj.type in ['method', 'function'] and not 'property' in obj.properties) -%}
       {%- if 'property' in obj.properties -%}
         {%- set label = 'prop' -%}
       {%- elif 'classmethod' in obj.properties -%}
         {%- set label = 'class' -%}
       {%- elif 'abstractmethod' in obj.properties -%}
         {%- set label = 'abc' -%}
       {%- elif 'staticmethod' in obj.properties -%}
         {%- set label = 'static' -%}
       {%- else -%}
         {%- set label = '' -%}
       {%- endif -%}
       {{- _item(obj, sig=sig, label=label) -}}
   {%- endfor -%}
{% endmacro %}

