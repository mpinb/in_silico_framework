from symtable import Symbol
from pygments.lexer import RegexLexer, bygroups
from pygments.token import *
from pygments.lexers._mapping import LEXERS
from pygments.lexers.python import PythonLexer

class NMODLLexer(RegexLexer):
    name = 'NMODL'
    aliases = ['nmodl']
    filenames = ['*.mod']
    tokens = {
        'root': [
            # Comments start with : or ?
            (r':.*', Comment),
            (r'\?.*', Comment),
            # Match blocks based on all-capital characters followed by { on the same line
            # But only match the actual captial letters
            # e.g. NEURON, DERIVATIVE, STATE, ASSIGNED etc
            (r'([A-Z]+)(?=.*{)', bygroups(Name.Builtin)),
            # Match keywords based on all-captial chars preceded and followed by whitespacae
            # e.g. SUFFIX, USEION etc.
            # Builtins are already matched above, so no need to worry about that
            (r'(?<=\s)[A-Z]+(?=\s)', Keyword),
            # Match ints and floats, except if preceded by text (e.g. in cm2 as unit)
            (r'(?<!\w)[0-9]*\.?[0-9]+', Number),
            # Match round and curly brackets
            (r'[\(\)]', Operator),
            (r'[\{\}]', Operator),
            # Match + - * / =
            (r'[\+\-\*\/\=]', Operator),
            # anything else
            (r'.', Text)
        ]
    }

def setup(app):
    app.add_lexer('NMODL', NMODLLexer)
