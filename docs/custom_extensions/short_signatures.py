from sphinx.domains.python import PyFunction, PyClasslike, PyMethod, PyObject
from sphinx import addnodes

class ShortSignaturePyObject(PyObject):
    """Adapt the Sphinx PyObject class to render short signatures.
    
    This does not impact Sphinx's ability to resolve these functions. Only the descname is adapted to a short version.
    """
    def handle_signature(self, sig, signode):
        # Call the base handler first (builds full signature & registers ID)
        fullname, prefix = super().handle_signature(sig, signode)

        # Strip all desc_addname nodes (these are the dotted module/class prefixes)
        signode.children = [
            child for child in signode.children
            if not isinstance(child, addnodes.desc_addname)
        ]

        return fullname, prefix

        
class ShortSignaturePyFunction(ShortSignaturePyObject, PyFunction): pass
class ShortSignaturePyMethod(ShortSignaturePyObject, PyMethod): pass
class ShortSignaturePyClasslike(ShortSignaturePyObject, PyClasslike): pass

def setup(app):
    app.add_directive_to_domain('py', 'function', ShortSignaturePyFunction)
    app.add_directive_to_domain('py', 'method', ShortSignaturePyMethod)
    app.add_directive_to_domain('py', 'class', ShortSignaturePyClasslike)