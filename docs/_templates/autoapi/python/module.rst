{%- import 'macros.rst' as macros %}
{%- set root_module = obj.id.split('.')[0] | escape %}
{%- set breadcrumb = obj.id.split('.')[1:] %}
{%- set shortname = obj.id.split('.')[-1] | escape %}

{% if obj.display %}
{% if breadcrumb %}
:mod:`{{ root_module }}`
{%- for n in range(breadcrumb|length )  %}
 ❭ :mod:`~{{ root_module }}.{{ breadcrumb[:n+1] | join('.') }}`
{%- endfor %}
{% endif %}


{{ shortname }}
{{ "=" * shortname|length }}

{% set visible_children = obj.children|selectattr("display")|rejectattr("imported")|list %}
{% set visible_classes = visible_children|selectattr("type", "equalto", "class")|list %}
{% set visible_functions = visible_children|selectattr("type", "equalto", "function")|list %}
{% set visible_attributes = visible_children|selectattr("type", "equalto", "data")|list %}
{% set visible_exceptions = visible_children|selectattr("type", "equalto", "exception")|list %}
{% set visible_submodules = obj.submodules|selectattr("display")|list %}
{% set visible_subpackages = obj.subpackages|selectattr("display")|list %}
{% set sidebar_entries = visible_classes + visible_functions + visible_exceptions %}
{% set visible_subs = visible_subpackages + visible_submodules%}
.. a hidden toctree for sidebar navigation
.. Include all visible children, except for attributes (makes things verbose)
.. These names need to match either a python object in the Python space, or (as done here) a direct link to an .rst file (without the suffix), either relative or absolute.
.. toctree::
   :hidden:

   {% for sub in visible_subs %}
   {{ sub.short_name }} <{{ sub.include_path }}>  
   {% endfor %}
   
   {%- for child in sidebar_entries %}
   {{ child.short_name }} <{{ child.include_path }}>
   {% endfor %}

.. py:module:: {{ obj.name }}

{% if obj.docstring %}
.. autoapi-nested-parse::
   {{ obj.docstring|indent(3) }}
{% endif %}


{%- if "show-module-summary" in autoapi_options %}
{% block classes scoped %}
{%- if visible_classes %}
{%- set public_classes = visible_classes|rejectattr('is_private_member')|list %}
{%- if public_classes %}
{{ macros.auto_summary(public_classes, title="Classes") }}
{%- endif %}
{%- endif %}
{%- endblock %}

{% block functions scoped %}
{%- if visible_functions %}
{%- set public_functions = visible_functions|rejectattr('is_private_member')|list %}
{%- if public_functions %}
{{ macros.auto_summary(public_functions, title="Functions") }}
{%- endif %}
{%- endif %}
{%- endblock %}

{% block subpackages %}
{%- if visible_subs %}
{%- set public_subs = visible_subs|rejectattr('is_private_member')|list %}
{%- if public_subs%}
{{ macros.auto_summary(public_subs, title="Modules") }}
{%- endif %}
{%- endif %}
{%- endblock %}

{% block exceptions %}
{%- if visible_exceptions %}
{{ macros.auto_summary(visible_exceptions, title="Exceptions") }}
{%- endif %}
{%- endblock %}
{% endif %}
{% endif %}
