"""Patch napoleon to work nicely with the sphinx-immaterial html theme

Sphinx immaterial interferes with Napoleon when ``napoleon.use_param=True``
When argument types are explicit directives e.g. :py:class:`a.b.Class`, sphinx-immaterial weirdly omits them from the final html, 
despite the fact they are perfectly fine and present in the rst stub files. 

On the other hand, the sphinx-immaterial html theme has a built-in python domain resolver (which is definitely not default for html themes, but really nice).
This means that these explicit directives ironically start working again when they are stripped of their directive, and just the content is passed to sphinx-immaterial.

So :py:class:`a.b.MyClass` will be omitted from the html, despite being explicit.
a.b.MyClass will render perfectly fine with working internal links.

This issue only exists when `napoleon.use_param=True` and Napoleon builds rst stubs with the :param myparam: role.
Otherwise, Napoleon uses a single :Parameters: block, which renders as a simple <ul> in html, and the directives remain untouched by sphinx-immaterial
"""
from sphinx.ext.napoleon.docstring import GoogleDocstring
import re


def _fixed_parse_parameters_section(self, section):
    """Override to preserve full class names in types."""
    lines = []
    for _name, _type, _desc in self._consume_fields():
        desc_lines = " ".join([e for e in _desc if e])
        if _type: # The type is defined in the docstring (very good)
            # Check if it is a directive
            pattern = re.compile(":(.+:)+`[~]?(?P<plain_type>.+)`")
            match = re.search(pattern, _type)
            # Fetch only the plain type from the directive
            plain_type = match.group("plain_type") if match else _type
            lines.extend([
                f':param {_name}: {desc_lines}',
                f':type {_name}: {plain_type}',  # Plain text type
                ''
            ])
        else:
            lines.extend([
                f':param {_name}: {desc_lines}',
                ''
            ])
    return lines

# Apply the fix
GoogleDocstring._parse_parameters_section = _fixed_parse_parameters_section