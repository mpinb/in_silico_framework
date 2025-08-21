# shortsig_links.py
from sphinx.domains import python
from sphinx import addnodes

def linked_handle_signature(self, sig, signode):
    fullname, prefix = self._orig_handle_signature(sig, signode)

    new_children = []
    for child in list(signode.children):
        if isinstance(child, addnodes.desc_addname):
            prefix_text = child.astext().rstrip(".")
            parts = prefix_text.split(".") if prefix_text else []

            for i, part in enumerate(parts):
                target = ".".join(parts[: i + 1])

                # Proper Sphinx-style cross-ref
                refnode = addnodes.pending_xref(
                    "",
                    refdomain="py",
                    reftype="mod",   # modules for now
                    reftarget=target,
                    modname=None,
                    classname=None,
                )
                refnode["refspecific"] = True
                refnode += addnodes.desc_name(part, part)

                new_children.append(refnode)

                if i < len(parts):
                    new_children.append(addnodes.desc_sig_punctuation(".", "."))

        else:
            new_children.append(child)

    # Replace children safely so parent pointers are set
    signode.children[:] = []
    for child in new_children:
        signode += child
    return fullname, prefix


def setup(app):
    if not hasattr(python.PyObject, "_orig_handle_signature"):
        python.PyObject._orig_handle_signature = python.PyObject.handle_signature
        python.PyObject.handle_signature = linked_handle_signature

    return {
        "version": "1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
