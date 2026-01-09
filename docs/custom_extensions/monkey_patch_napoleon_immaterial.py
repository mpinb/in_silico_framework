"""Patch napoleon to work nicely with the sphinx-immaterial html theme

Sphinx immaterial interferes with Napoleon when ``napoleon.use_param=True``
When argument types are explicit directives e.g. :class:`a.b.Class`, sphinx-immaterial weirdly omits them from the final html, 
despite the fact they are perfectly fine and present in the rst stub files. 

On the other hand, the sphinx-immaterial html theme has a built-in python domain resolver (which is definitely not default for html themes, but really nice).
This means that these explicit directives ironically start working again when they are stripped of their directive, and just the content is passed to sphinx-immaterial.

So :class:`~a.b.MyClass` will be omitted from the html, despite being an explicit role.
On the other hand: ~a.b.MyClass will render perfectly fine with working internal links, as long as it's in an argument block or inside numpy style directive-like syntax.

This issue only exists when `napoleon.use_param=True` and Napoleon builds rst stubs with the :param myparam: role.
Otherwise, Napoleon uses a single :Parameters: block, which renders as a simple <ul> in html, and the directives remain untouched by sphinx-immaterial

One option is to change all the argument types to be simple FQNs instead of explicit roles. This may break other themes (if we ever choose to migrate)
Another option is to monkey patch immaterial OR napoleon so they work nicely together.
We monkey-patch napoleon here to strip out the FQN from explicit roles in argument blocks.
"""
from sphinx.ext.napoleon.docstring import GoogleDocstring
import re

def _format_docutils_params(
    self, 
    fields: list[tuple[str, str, list[str]]],
    field_role: str = 'param', 
    type_role: str = 'type'
) -> list[str]:
    
    lines = []
    for _name, _type, _desc in fields:
        _desc = self._strip_empty(_desc)
        if any(_desc):
            _desc = self._fix_field_desc(_desc)
            field = f':{field_role} {_name}: '
            lines.extend(self._format_block(field, _desc))
        else:
            lines.append(f':{field_role} {_name}:')

        if _type:
            # ------------------ start patch
            pattern = re.compile(":(.+:)+`(?P<plain_type>.+)`") # Check if it is a directive
            match = re.search(pattern, _type)
            _type = match.group("plain_type") if match else _type
            # -------------------- end patch
            lines.append(f':{type_role} {_name}: {_type}')
            
    return lines + ['']

def setup(app):
    GoogleDocstring._format_docutils_params = _format_docutils_params
