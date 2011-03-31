# -*- coding: utf-8 -*-
"""
    The Pygments Markdown Preprocessor
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    This fragment is a Markdown_ preprocessor that renders source code
    to HTML via Pygments.  To use it, invoke Markdown like so::

        from markdown import Markdown

        md = Markdown()
        md.textPreprocessors.insert(0, CodeBlockPreprocessor())
        html = md.convert(someText)

    markdown is then a callable that can be passed to the context of
    a template and used in that template, for example.

    This uses CSS classes by default, so use
    ``pygmentize -S <some style> -f html > pygments.css``
    to create a stylesheet to be added to the website.

    You can then highlight source code in your markdown markup::

        [sourcecode:lexer]
        some code
        [/sourcecode]

    .. _Markdown: http://www.freewisdom.org/projects/python-markdown/

    :copyright: Copyright 2006-2009 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

# Options
# ~~~~~~~

# Set to True if you want inline CSS styles instead of classes
INLINESTYLES = False
LINEENDING = '<br />'


import re

from markdown import TextPreprocessor

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, TextLexer


class CodeBlockPreprocessor(TextPreprocessor):

    pattern = re.compile(
        r'\s*\[sourcecode:(.+?)\](.+?)\[/sourcecode\]\s*', re.S)

    formatter = HtmlFormatter(noclasses=INLINESTYLES, lineseparator=LINEENDING, linenos='inline')

    def run(self, lines):
        def repl(m):
            try:
                lexer = get_lexer_by_name(m.group(1))
            except ValueError:
                lexer = TextLexer()
            code = highlight(m.group(2), lexer, self.formatter)
            i = code.rfind("%s</pre></div>" % LINEENDING)
            code = code[:i] + code[i+len(LINEENDING):]
            return "\n\n%s\n\n" % code.strip()
        return self.pattern.sub(
            repl, lines)
