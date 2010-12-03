#!/usr/bin/env python
"""
PyTextile

A Humane Web Text Generator
"""

__version__ = '2.1.3'

__date__ = '2009/02/07'

__copyright__ = """
Copyright (c) 2009, Jason Samsa, http://jsamsa.com/
Copyright (c) 2004, Roberto A. F. De Almeida, http://dealmeida.net/
Copyright (c) 2003, Mark Pilgrim, http://diveintomark.org/

Original PHP Version:
Copyright (c) 2003-2004, Dean Allen <dean@textism.com>
All rights reserved.

Thanks to Carlo Zottmann <carlo@g-blog.net> for refactoring
Textile's procedural code into a class framework

Additions and fixes Copyright (c) 2006 Alex Shiels http://thresholdstate.com/

"""

__license__ = """
L I C E N S E
=============
Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice,
  this list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

* Neither the name Textile nor the names of its contributors may be used to
  endorse or promote products derived from this software without specific
  prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.

"""

import re
import uuid
from urlparse import urlparse
import sgmllib

def _normalize_newlines(string):
    import re
    out = re.sub(r'\r\n', '\n', string)
    out = re.sub(r'\n{3,}', '\n\n', out)
    out = re.sub(r'\n\s*\n', '\n\n', out)
    out = re.sub(r'"$', '" ', out)
    return out

# PyTextile can optionally sanitize the generated XHTML,
# which is good for weblog comments. This code is from
# Mark Pilgrim's feedparser.
class _BaseHTMLProcessor(sgmllib.SGMLParser):
    elements_no_end_tag = ['area', 'base', 'basefont', 'br', 'col', 'frame', 'hr',
      'img', 'input', 'isindex', 'link', 'meta', 'param']

    def __init__(self):
        sgmllib.SGMLParser.__init__(self)

    def reset(self):
        self.pieces = []
        sgmllib.SGMLParser.reset(self)

    def normalize_attrs(self, attrs):
        # utility method to be called by descendants
        attrs = [(k.lower(), sgmllib.charref.sub(lambda m: unichr(int(m.groups()[0])), v).strip()) for k, v in attrs]
        attrs = [(k, k in ('rel', 'type') and v.lower() or v) for k, v in attrs]
        return attrs

    def unknown_starttag(self, tag, attrs):
        # called for each start tag
        # attrs is a list of (attr, value) tuples
        # e.g. for <pre class="screen">, tag="pre", attrs=[("class", "screen")]
        strattrs = "".join([' %s="%s"' % (key, value) for key, value in attrs])
        if tag in self.elements_no_end_tag:
            self.pieces.append("<%(tag)s%(strattrs)s />" % locals())
        else:
            self.pieces.append("<%(tag)s%(strattrs)s>" % locals())

    def unknown_endtag(self, tag):
        # called for each end tag, e.g. for </pre>, tag will be "pre"
        # Reconstruct the original end tag.
        if tag not in self.elements_no_end_tag:
            self.pieces.append("</%(tag)s>" % locals())

    def handle_charref(self, ref):
        # called for each character reference, e.g. for "&#160;", ref will be "160"
        # Reconstruct the original character reference.
        self.pieces.append("&#%(ref)s;" % locals())

    def handle_entityref(self, ref):
        # called for each entity reference, e.g. for "&copy;", ref will be "copy"
        # Reconstruct the original entity reference.
        self.pieces.append("&%(ref)s;" % locals())

    def handle_data(self, text):
        # called for each block of plain text, i.e. outside of any tag and
        # not containing any character or entity references
        # Store the original text verbatim.
        self.pieces.append(text)

    def handle_comment(self, text):
        # called for each HTML comment, e.g. <!-- insert Javascript code here -->
        # Reconstruct the original comment.
        self.pieces.append("<!--%(text)s-->" % locals())

    def handle_pi(self, text):
        # called for each processing instruction, e.g. <?instruction>
        # Reconstruct original processing instruction.
        self.pieces.append("<?%(text)s>" % locals())

    def handle_decl(self, text):
        # called for the DOCTYPE, if present, e.g.
        # <!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
        #     "http://www.w3.org/TR/html4/loose.dtd">
        # Reconstruct original DOCTYPE
        self.pieces.append("<!%(text)s>" % locals())

    def output(self):
        """Return processed HTML as a single string"""
        return "".join(self.pieces)


class _HTMLSanitizer(_BaseHTMLProcessor):
    acceptable_elements = ['a', 'abbr', 'acronym', 'address', 'area', 'b', 'big',
      'blockquote', 'br', 'button', 'caption', 'center', 'cite', 'code', 'col',
      'colgroup', 'dd', 'del', 'dfn', 'dir', 'div', 'dl', 'dt', 'em', 'fieldset',
      'font', 'form', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'i', 'img', 'input',
      'ins', 'kbd', 'label', 'legend', 'li', 'map', 'menu', 'ol', 'optgroup',
      'option', 'p', 'pre', 'q', 's', 'samp', 'select', 'small', 'span', 'strike',
      'strong', 'sub', 'sup', 'table', 'tbody', 'td', 'textarea', 'tfoot', 'th',
      'thead', 'tr', 'tt', 'u', 'ul', 'var']

    acceptable_attributes = ['abbr', 'accept', 'accept-charset', 'accesskey',
      'action', 'align', 'alt', 'axis', 'border', 'cellpadding', 'cellspacing',
      'char', 'charoff', 'charset', 'checked', 'cite', 'class', 'clear', 'cols',
      'colspan', 'color', 'compact', 'coords', 'datetime', 'dir', 'disabled',
      'enctype', 'for', 'frame', 'headers', 'height', 'href', 'hreflang', 'hspace',
      'id', 'ismap', 'label', 'lang', 'longdesc', 'maxlength', 'media', 'method',
      'multiple', 'name', 'nohref', 'noshade', 'nowrap', 'prompt', 'readonly',
      'rel', 'rev', 'rows', 'rowspan', 'rules', 'scope', 'selected', 'shape', 'size',
      'span', 'src', 'start', 'summary', 'tabindex', 'target', 'title', 'type',
      'usemap', 'valign', 'value', 'vspace', 'width']

    unacceptable_elements_with_end_tag = ['script', 'applet']

    # This if for MathML.
    mathml_elements = ['math', 'mi', 'mn', 'mo', 'mrow', 'msup']
    mathml_attributes = ['mode', 'xmlns']

    acceptable_elements = acceptable_elements + mathml_elements
    acceptable_attributes = acceptable_attributes + mathml_attributes

    def reset(self):
        _BaseHTMLProcessor.reset(self)
        self.unacceptablestack = 0

    def unknown_starttag(self, tag, attrs):
        if not tag in self.acceptable_elements:
            if tag in self.unacceptable_elements_with_end_tag:
                self.unacceptablestack += 1
            return
        attrs = self.normalize_attrs(attrs)
        attrs = [(key, value) for key, value in attrs if key in self.acceptable_attributes]
        _BaseHTMLProcessor.unknown_starttag(self, tag, attrs)

    def unknown_endtag(self, tag):
        if not tag in self.acceptable_elements:
            if tag in self.unacceptable_elements_with_end_tag:
                self.unacceptablestack -= 1
            return
        _BaseHTMLProcessor.unknown_endtag(self, tag)

    def handle_pi(self, text):
        pass

    def handle_decl(self, text):
        pass

    def handle_data(self, text):
        if not self.unacceptablestack:
            _BaseHTMLProcessor.handle_data(self, text)


# PyTextile can optionally validate the generated
# XHTML code using either mxTidy or uTidyLib.
try:
    # This is mxTidy.
    from mx.Tidy import Tidy

    def _tidy1(text):
        """mxTidy's XHTML validator.

        This function is a wrapper to mxTidy's validator.
        """
        nerrors, nwarnings, text, errortext = Tidy.tidy(text, output_xhtml=1, numeric_entities=1, wrap=0)
        return _in_tag(text, 'body')

    _tidy = _tidy1

except ImportError:
    try:
        # This is uTidyLib.
        import tidy

        def _tidy2(text):
            """uTidyLib's XHTML validator.

            This function is a wrapper to uTidyLib's validator.
            """
            text = tidy.parseString(text,  output_xhtml=1, add_xml_decl=0, indent=0, tidy_mark=0)
            return _in_tag(str(text), 'body')

        _tidy = _tidy2

    except ImportError:
        _tidy = None

class Textile(object):
    hlgn = r'(?:\<(?!>)|(?<!<)\>|\<\>|\=|[()]+(?! ))'
    vlgn = r'[\-^~]'
    clas = r'(?:\([^)]+\))'
    lnge = r'(?:\[[^\]]+\])'
    styl = r'(?:\{[^}]+\})'
    cspn = r'(?:\\\d+)'
    rspn = r'(?:\/\d+)'
    a = r'(?:%s|%s)*' % (hlgn, vlgn)
    s = r'(?:%s|%s)*' % (cspn, rspn)
    c = r'(?:%s)*' % '|'.join([clas, styl, lnge, hlgn])

    pnct = r'[-!"#$%&()*+,/:;<=>?@\'\[\\\]\.^_`{|}~]'
    # urlch = r'[\w"$\-_.+!*\'(),";/?:@=&%#{}|\\^~\[\]`]'
    urlch = '[\w"$\-_.+*\'(),";\/?:@=&%#{}|\\^~\[\]`]'

    url_schemes = ('http','https','ftp','mailto')

    btag = ('bq', 'bc', 'notextile', 'pre', 'h[1-6]', 'fn\d+', 'p')
    noimage = False
    hu = ''

    glyph_defaults = (
        ('txt_quote_single_open',  '&#8216;'),
        ('txt_quote_single_close', '&#8217;'),
        ('txt_quote_double_open',  '&#8220;'),
        ('txt_quote_double_close', '&#8221;'),
        ('txt_apostrophe',         '&#8217;'),
        ('txt_prime',              '&#8242;'),
        ('txt_prime_double',       '&#8243;'),
        ('txt_ellipsis',           '&#8230;'),
        ('txt_emdash',             '&#8212;'),
        ('txt_endash',             '&#8211;'),
        ('txt_dimension',          '&#215;'),
        ('txt_trademark',          '&#8482;'),
        ('txt_registered',         '&#174;'),
        ('txt_copyright',          '&#169;'),
    )

    def __init__(self, restricted=False, lite=False):
        """docstring for __init__"""
        self.restricted = restricted
        self.lite = lite
        self.fn = {}
        self.urlrefs = {}
        self.shelf = {}
        self.rel = ''

    def textile(self, text, rel=None, encoding='utf8', output='utf8', validate=False, sanitize=False, head_offset='ignored'):
        """
        >>> import textile
        >>> textile.textile('some textile')
        '\\t<p>some textile</p>'
        """
        text = _normalize_newlines(text)

        if rel:
            self.rel = ' rel="%s"' % rel

        text = self.getRefs(text)

        if not self.lite:
            text = self.block(text)

        text = self.retrieve(text)

        # Convert to desired output.
        if isinstance(text, str):
            text = unicode(text, encoding)
 
        text = text.encode(output, 'xmlcharrefreplace')

        # Sanitize?
        if sanitize:
            p = _HTMLSanitizer()
            p.feed(text)
            text = p.output()

        # Validate output.
        if _tidy and validate:
            text = _tidy(text)

        return text

    def pba(self, input, element=None):
        """
        >>> t = Textile()
        >>> t.pba(r'\3')
        ''
        >>> t.pba(r'\\3', element='td')
        ' colspan="3"'
        >>> t.pba(r'/4', element='td')
        ' rowspan="4"'
        >>> t.pba(r'\\3/4', element='td')
        ' colspan="3" rowspan="4"'

        >>> t.vAlign('^')
        'top'

        >>> t.pba('^', element='td')
        ' style="vertical-align:top;"'

        >>> t.pba('{line-height:18px}')
        ' style="line-height:18px;"'

        >>> t.pba('(foo-bar)')
        ' class="foo-bar"'

        >>> t.pba('(#myid)')
        ' id="myid"'

        >>> t.pba('(foo-bar#myid)')
        ' class="foo-bar" id="myid"'

        >>> t.pba('((((')
        ' style="padding-left:4em;"'

        >>> t.pba(')))')
        ' style="padding-right:3em;"'

        >>> t.pba('[fr]')
        ' lang="fr"'

        """
        style = []
        aclass = ''
        lang = ''
        colspan = ''
        rowspan = ''
        id = ''
        atts = ''

        if not input: return ''

        matched = input
        if element == 'td':
            m = re.search(r'\\(\d+)', matched)
            if m:
                colspan = m.group(1)

            m = re.search(r'/(\d+)', matched)
            if m:
                rowspan = m.group(1)

        if element == 'td' or element == 'tr':
            m = re.search(r'(%s)' % self.vlgn, matched)
            if m: style.append("vertical-align:%s;" % self.vAlign(m.group(1)))

        m = re.search(r'\{([^}]*)\}', matched)
        if m:
            style.append(m.group(1).rstrip(';') + ';')
            matched = matched.replace(m.group(0), '')

        m = re.search(r'\[([^\]]+)\]', matched, re.U)
        if m:
            lang = m.group(1)
            matched = matched.replace(m.group(0), '')

        m = re.search(r'\(([^()]+)\)', matched, re.U)
        if m:
            aclass = m.group(1)
            matched = matched.replace(m.group(0), '')

        m = re.search(r'([(]+)', matched)
        if m:
            style.append("padding-left:%sem;" % len(m.group(1)))
            matched = matched.replace(m.group(0), '')

        m = re.search(r'([)]+)', matched)
        if m:
            style.append("padding-right:%sem;" % len(m.group(1)))
            matched = matched.replace(m.group(0), '')

        m = re.search(r'(%s)' % self.hlgn, matched)
        if m:
            style.append("text-align:%s;" % self.hAlign(m.group(1)))

        m = re.search(r'^(.*)#(.*)$', aclass)
        if m:
            id = m.group(2)
            aclass = m.group(1)

        if self.restricted:
            if lang: return ' lang="%s"'
            else: return ''

        result = []
        if style: result.append(' style="%s"' % "".join(style))
        if aclass: result.append(' class="%s"' % aclass)
        if lang: result.append(' lang="%s"' % lang)
        if id: result.append(' id="%s"' % id)
        if colspan: result.append(' colspan="%s"' % colspan)
        if rowspan: result.append(' rowspan="%s"' % rowspan)
        return ''.join(result)

    def hasRawText(self, text):
        """
        checks whether the text has text not already enclosed by a block tag

        >>> t = Textile()
        >>> t.hasRawText('<p>foo bar biz baz</p>')
        False

        >>> t.hasRawText(' why yes, yes it does')
        True

        """
        r = re.compile(r'<(p|blockquote|div|form|table|ul|ol|pre|h\d)[^>]*?>.*</\1>', re.S).sub('', text.strip()).strip()
        r = re.compile(r'<(hr|br)[^>]*?/>').sub('', r)
        return '' != r

    def table(self, text):
        r"""
        >>> t = Textile()
        >>> t.table('|one|two|three|\n|a|b|c|')
        '\t<table>\n\t\t<tr>\n\t\t\t<td>one</td>\n\t\t\t<td>two</td>\n\t\t\t<td>three</td>\n\t\t</tr>\n\t\t<tr>\n\t\t\t<td>a</td>\n\t\t\t<td>b</td>\n\t\t\t<td>c</td>\n\t\t</tr>\n\t</table>\n\n'
        """
        text = text + "\n\n"
        pattern = re.compile(r'^(?:table(_?%(s)s%(a)s%(c)s)\. ?\n)?^(%(a)s%(c)s\.? ?\|.*\|)\n\n' % {'s':self.s, 'a':self.a, 'c':self.c}, re.S|re.M|re.U)
        return pattern.sub(self.fTable, text)

    def fTable(self, match):
        tatts = self.pba(match.group(1), 'table')
        rows = []
        for row in [ x for x in match.group(2).split('\n') if x]:
            rmtch = re.search(r'^(%s%s\. )(.*)' % (self.a, self.c), row.lstrip())
            if rmtch:
                ratts = self.pba(rmtch.group(1), 'tr')
                row = rmtch.group(2)
            else: ratts = ''

            cells = []
            for cell in row.split('|'):
                ctyp = 'd'
                if re.search(r'^_', cell): ctyp = "h"
                cmtch = re.search(r'^(_?%s%s%s\. )(.*)' % (self.s, self.a, self.c), cell)
                if cmtch:
                    catts = self.pba(cmtch.group(1), 'td')
                    cell = cmtch.group(2)
                else: catts = ''

                cell = self.graf(self.span(cell))

                if cell.strip() != '':
                    cells.append('\t\t\t<t%s%s>%s</t%s>' % (ctyp, catts, cell, ctyp))
            rows.append("\t\t<tr%s>\n%s\n\t\t</tr>" % (ratts, '\n'.join(cells)))
            cells = []
            catts = None
        return "\t<table%s>\n%s\n\t</table>\n\n" % (tatts, '\n'.join(rows))

    def lists(self, text):
        """
        >>> t = Textile()
        >>> t.lists("* one\\n* two\\n* three")
        '\\t<ul>\\n\\t\\t<li>one</li>\\n\\t\\t<li>two</li>\\n\\t\\t<li>three</li>\\n\\t</ul>'
        """
        pattern = re.compile(r'^([#*]+%s .*)$(?![^#*])' % self.c, re.U|re.M|re.S)
        return pattern.sub(self.fList, text)

    def fList(self, match):
        text = match.group(0).split("\n")
        result = []
        lists = []
        for i, line in enumerate(text):
            try:
                nextline = text[i+1]
            except IndexError:
                nextline = ''

            m = re.search(r"^([#*]+)(%s%s) (.*)$" % (self.a, self.c), line, re.S)
            if m:
                tl, atts, content = m.groups()
                nl = ''
                nm = re.search(r'^([#*]+)\s.*', nextline)
                if nm:
                    nl = nm.group(1)
                if tl not in lists:
                    lists.append(tl)
                    atts = self.pba(atts)
                    line = "\t<%sl%s>\n\t\t<li>%s" % (self.lT(tl), atts, self.graf(content))
                else:
                    line = "\t\t<li>" + self.graf(content)

                if len(nl) <= len(tl): line = line + "</li>"
                for k in reversed(lists):
                    if len(k) > len(nl):
                        line = line + "\n\t</%sl>" % self.lT(k)
                        if len(k) > 1:
                            line = line + "</li>"
                        lists.remove(k)

            result.append(line)
        return "\n".join(result)

    def lT(self, input):
        if re.search(r'^#+', input):
            return 'o'
        else:
            return 'u'

    def doPBr(self, in_):
        return re.compile(r'<(p)([^>]*?)>(.*)(</\1>)', re.S).sub(self.doBr, in_)

    def doBr(self, match):
        content = re.sub(r'(.+)(?:(?<!<br>)|(?<!<br />))\n(?![#*\s|])', '\\1<br />', match.group(3))
        return '<%s%s>%s%s' % (match.group(1), match.group(2), content, match.group(4))

    def block(self, text):
        """
        >>> t = Textile()
        >>> t.block('h1. foobar baby')
        '\\t<h1>foobar baby</h1>'
        """
        tre = '|'.join(self.btag)
        text = text.split('\n\n')

        tag = 'p'
        atts = cite = graf = ext = ''

        out = []

        anon = False
        for line in text:
            pattern = r'^(%s)(%s%s)\.(\.?)(?::(\S+))? (.*)$' % (tre, self.a, self.c)
            match = re.search(pattern, line, re.S)
            if match:
                if ext:
                    out.append(out.pop() + c1)

                tag,atts,ext,cite,graf = match.groups()
                o1, o2, content, c2, c1 = self.fBlock(tag, atts, ext, cite, graf)
                # leave off c1 if this block is extended, we'll close it at the start of the next block
                if ext:
                    line = "%s%s%s%s" % (o1, o2, content, c2)
                else:
                    line = "%s%s%s%s%s" % (o1, o2, content, c2, c1)

            else:
                anon = True
                if ext or not re.search(r'^\s', line):
                    o1, o2, content, c2, c1 = self.fBlock(tag, atts, ext, cite, line)
                    # skip $o1/$c1 because this is part of a continuing extended block
                    if tag == 'p' and not self.hasRawText(content):
                        line = content
                    else:
                        line = "%s%s%s" % (o2, content, c2)
                else:
                    line = self.graf(line)

            line = self.doPBr(line)
            line = re.sub(r'<br>', '<br />', line)

            if ext and anon:
                out.append(out.pop() + "\n" + line)
            else:
                out.append(line)

            if not ext:
                tag = 'p'
                atts = ''
                cite = ''
                graf = ''

        if ext:
            out.append(out.pop() + c1)
        return '\n\n'.join(out)

    def fBlock(self, tag, atts, ext, cite, content):
        """
        >>> t = Textile()
        >>> t.fBlock("bq", "", None, "", "Hello BlockQuote")
        ('\\t<blockquote>\\n', '\\t\\t<p>', 'Hello BlockQuote', '</p>', '\\n\\t</blockquote>')

        >>> t.fBlock("bq", "", None, "http://google.com", "Hello BlockQuote")
        ('\\t<blockquote cite="http://google.com">\\n', '\\t\\t<p>', 'Hello BlockQuote', '</p>', '\\n\\t</blockquote>')

        >>> t.fBlock("bc", "", None, "", 'printf "Hello, World";') # doctest: +ELLIPSIS
        ('<pre>', '<code>', ..., '</code>', '</pre>')

        >>> t.fBlock("h1", "", None, "", "foobar")
        ('', '\\t<h1>', 'foobar', '</h1>', '')
        """
        atts = self.pba(atts)
        o1 = o2 = c2 = c1 = ''

        m = re.search(r'fn(\d+)', tag)
        if m:
            tag = 'p'
            if m.group(1) in self.fn:
                fnid = self.fn[m.group(1)]
            else:
                fnid = m.group(1)
            atts = atts + ' id="fn%s"' % fnid
            if atts.find('class=') < 0:
                atts = atts + ' class="footnote"'
            content = ('<sup>%s</sup>' % m.group(1)) + content

        if tag == 'bq':
            cite = self.checkRefs(cite)
            if cite:
                cite = ' cite="%s"' % cite
            else:
                cite = ''
            o1 = "\t<blockquote%s%s>\n" % (cite, atts)
            o2 = "\t\t<p%s>" % atts
            c2 = "</p>"
            c1 = "\n\t</blockquote>"

        elif tag == 'bc':
            o1 = "<pre%s>" % atts
            o2 = "<code%s>" % atts
            c2 = "</code>"
            c1 = "</pre>"
            content = self.shelve(self.encode_html(content.rstrip("\n") + "\n"))

        elif tag == 'notextile':
            content = self.shelve(content)
            o1 = o2 = ''
            c1 = c2 = ''

        elif tag == 'pre':
            content = self.shelve(self.encode_html(content.rstrip("\n") + "\n"))
            o1 = "<pre%s>" % atts
            o2 = c2 = ''
            c1 = '</pre>'

        else:
            o2 = "\t<%s%s>" % (tag, atts)
            c2 = "</%s>" % tag

        content = self.graf(content)
        return o1, o2, content, c2, c1

    def footnoteRef(self, text):
        """
        >>> t = Textile()
        >>> t.footnoteRef('foo[1] ') # doctest: +ELLIPSIS
        'foo<sup class="footnote"><a href="#fn...">1</a></sup> '
        """
        return re.sub(r'\b\[([0-9]+)\](\s)?', self.footnoteID, text)

    def footnoteID(self, match):
        id, t = match.groups()
        if id not in self.fn:
            self.fn[id] = str(uuid.uuid4())
        fnid = self.fn[id]
        if not t: t = ''
        return '<sup class="footnote"><a href="#fn%s">%s</a></sup>%s' % (fnid, id, t)

    def glyphs(self, text):
        """
        >>> t = Textile()

        >>> t.glyphs("apostrophe's")
        'apostrophe&#8217;s'

        >>> t.glyphs("back in '88")
        'back in &#8217;88'

        >>> t.glyphs('foo ...')
        'foo &#8230;'

        >>> t.glyphs('--')
        '&#8212;'

        >>> t.glyphs('FooBar[tm]')
        'FooBar&#8482;'

        >>> t.glyphs("<p><cite>Cat's Cradle</cite> by Vonnegut</p>")
        '<p><cite>Cat&#8217;s Cradle</cite> by Vonnegut</p>'

        """
         # fix: hackish
        text = re.sub(r'"\z', '\" ', text)

        glyph_search = (
            re.compile(r"(\w)\'(\w)"),                                      # apostrophe's
            re.compile(r'(\s)\'(\d+\w?)\b(?!\')'),                          # back in '88
            re.compile(r'(\S)\'(?=\s|'+self.pnct+'|<|$)'),                       #  single closing
            re.compile(r'\'/'),                                             #  single opening
            re.compile(r'(\S)\"(?=\s|'+self.pnct+'|<|$)'),                       #  double closing
            re.compile(r'"'),                                               #  double opening
            re.compile(r'\b([A-Z][A-Z0-9]{2,})\b(?:[(]([^)]*)[)])'),        #  3+ uppercase acronym
            re.compile(r'\b([A-Z][A-Z\'\-]+[A-Z])(?=[\s.,\)>])'),           #  3+ uppercase
            re.compile(r'\b(\s{0,1})?\.{3}'),                                     #  ellipsis
            re.compile(r'(\s?)--(\s?)'),                                    #  em dash
            re.compile(r'\s-(?:\s|$)'),                                     #  en dash
            re.compile(r'(\d+)( ?)x( ?)(?=\d+)'),                           #  dimension sign
            re.compile(r'\b ?[([]TM[])]', re.I),                            #  trademark
            re.compile(r'\b ?[([]R[])]', re.I),                             #  registered
            re.compile(r'\b ?[([]C[])]', re.I),                             #  copyright
         )

        glyph_replace = [x % dict(self.glyph_defaults) for x in (
            r'\1%(txt_apostrophe)s\2',           # apostrophe's
            r'\1%(txt_apostrophe)s\2',           # back in '88
            r'\1%(txt_quote_single_close)s',     #  single closing
            r'%(txt_quote_single_open)s',         #  single opening
            r'\1%(txt_quote_double_close)s',        #  double closing
            r'%(txt_quote_double_open)s',             #  double opening
            r'<acronym title="\2">\1</acronym>', #  3+ uppercase acronym
            r'<span class="caps">\1</span>',     #  3+ uppercase
            r'\1%(txt_ellipsis)s',                  #  ellipsis
            r'\1%(txt_emdash)s\2',               #  em dash
            r' %(txt_endash)s ',                 #  en dash
            r'\1\2%(txt_dimension)s\3',          #  dimension sign
            r'%(txt_trademark)s',                #  trademark
            r'%(txt_registered)s',                #  registered
            r'%(txt_copyright)s',                #  copyright
        )]

        result = []
        for line in re.compile(r'(<.*?>)', re.U).split(text):
            if not re.search(r'<.*>', line):
                for s, r in zip(glyph_search, glyph_replace):
                    line = s.sub(r, line)
            result.append(line)
        return ''.join(result)

    def iAlign(self, input):
        d = {'<':'left', '=':'center', '>':'right'}
        return d.get(input, '')

    def vAlign(self, input):
        d = {'^':'top', '-':'middle', '~':'bottom'}
        return d.get(input, '')

    def hAlign(self, input):
        d = {'<':'left', '=':'center', '>':'right', '<>': 'justify'}
        return d.get(input, '')

    def getRefs(self, text):
        """
        what is this for?
        """
        pattern = re.compile(r'(?:(?<=^)|(?<=\s))\[(.+)\]((?:http:\/\/|\/)\S+)(?=\s|$)', re.U)
        text = pattern.sub(self.refs, text)
        return text

    def refs(self, match):
        flag, url = match.groups()
        self.urlrefs[flag] = url
        return ''

    def checkRefs(self, url):
        return self.urlrefs.get(url, url)

    def relURL(self, url):
        o = urlparse(url)
        (scheme,netloc,path,params,query,fragment) = o[0:6]
        if (not scheme or scheme == 'http') and not netloc and re.search(r'^\w', path):
            url = self.hu + url
        if self.restricted and scheme and scheme not in self.url_schemes:
            return '#'
        return url

    def shelve(self, text):
        id = str(uuid.uuid4())
        self.shelf[id] = text
        return id

    def retrieve(self, text):
        """
        >>> t = Textile()
        >>> id = t.shelve("foobar")
        >>> t.retrieve(id)
        'foobar'
        """
        while True:
            old = text
            for k,v in self.shelf.items():
                text = text.replace(k,v)
            if text == old: break
        return text

    def encode_html(self, text, quotes=True):
        a = (
            ('&', '&#38;'),
            ('<', '&#60;'),
            ('>', '&#62;')
        )

        if quotes:
            a = a + (
                ("'", '&#39;'),
                ('"', '&#34;')
            )

        for k,v in a:
            text = text.replace(k,v)
        return text

    def graf(self, text):
        if not self.lite:
            text = self.noTextile(text)
            text = self.code(text)

        text = self.links(text)

        if not self.noimage:
            text = self.image(text)

        if not self.lite:
            text = self.lists(text)
            text = self.table(text)

        text = self.span(text)
        text = self.footnoteRef(text)
        text = self.glyphs(text)

        return text.rstrip('\n')

    def links(self, text):
        """
        >>> t = Textile()
        >>> t.links('fooobar "Google":http://google.com/foobar/ and hello world "flickr":http://flickr.com/photos/jsamsa/ ') # doctest: +ELLIPSIS
        'fooobar ... and hello world ...'
        """

        punct = '!"#$%&\'*+,-./:;=?@\\^_`|~'

        pattern = r'''
            ([\s\[{(]|[%s])?     # $pre
            "                          # start
            (%s)                     # $atts
            ([^"]+?)                   # $text
            \s?
            (?:\(([^)]+?)\)(?="))?     # $title
            ":
            (\S+?)                     # $url
            (\/)?                      # $slash
            ([^\w\/;]*?)               # $post
            (?=<|\s|$)
        ''' % (re.escape(punct), self.c)

        text = re.compile(pattern, re.X).sub(self.fLink, text)

        return text

    def fLink(self, match):
        pre, atts, text, title, url, slash, post = match.groups()

        if pre == None:
            pre = ''
            
        url = self.checkRefs(url)

        atts = self.pba(atts)
        if title: atts = atts +  ' title="%s"' % self.encode_html(title)

        if not self.noimage:
            text = self.image(text)

        text = self.span(text)
        text = self.glyphs(text)

        url = self.relURL(url)
        if slash: url = url + slash
        out = '<a href="%s"%s%s>%s</a>' % (self.encode_html(url), atts, self.rel, text)
        out = self.shelve(out)
        return ''.join([pre, out, post])

    def span(self, text):
        """
        >>> t = Textile()
        >>> t.span(r"hello %(bob)span *strong* and **bold**% goodbye")
        'hello <span class="bob">span <strong>strong</strong> and <b>bold</b></span> goodbye'
        """
        qtags = (r'\*\*', r'\*', r'\?\?', r'\-', r'__', r'_', r'%', r'\+', r'~', r'\^')
        pnct = ".,\"'?!;:"

        for qtag in qtags:
            pattern = re.compile(r"""
                (?:^|(?<=[\s>%(pnct)s])|([\]}]))
                (%(qtag)s)(?!%(qtag)s)
                (%(c)s)
                (?::(\S+))?
                ([^\s%(qtag)s]+|\S[^%(qtag)s\n]*[^\s%(qtag)s\n])
                ([%(pnct)s]*)
                %(qtag)s
                (?:$|([\]}])|(?=%(selfpnct)s{1,2}|\s))
            """ % {'qtag':qtag,'c':self.c,'pnct':pnct,'selfpnct':self.pnct}, re.X)
            text = pattern.sub(self.fSpan, text)
        return text


    def fSpan(self, match):
        _, tag, atts, cite, content, end, _ = match.groups()

        qtags = {
            '*': 'strong',
            '**': 'b',
            '??': 'cite',
            '_' : 'em',
            '__': 'i',
            '-' : 'del',
            '%' : 'span',
            '+' : 'ins',
            '~' : 'sub',
            '^' : 'sup'
        }
        tag = qtags[tag]
        atts = self.pba(atts)
        if cite:
            atts = atts + 'cite="%s"' % cite

        out = "<%s%s>%s%s</%s>" % (tag, atts, content, end, tag)
        return out;

    def image(self, text):
        """
        >>> t = Textile()
        >>> t.image('!/imgs/myphoto.jpg!:http://jsamsa.com')
        '<a href="http://jsamsa.com"><img src="/imgs/myphoto.jpg" alt="" /></a>'
        """
        pattern = re.compile(r"""
            (?:[\[{])?          # pre
            \!                 # opening !
            (\<|\=|\>)??       # optional alignment atts
            (%s)               # optional style,class atts
            (?:\. )?           # optional dot-space
            ([^\s(!]+)         # presume this is the src
            \s?                # optional space
            (?:\(([^\)]+)\))?  # optional title
            \!                 # closing
            (?::(\S+))?        # optional href
            (?:[\]}]|(?=\s|$)) # lookahead: space or end of string
        """ % self.c, re.U|re.X)
        return pattern.sub(self.fImage, text)

    def fImage(self, match):
        # (None, '', '/imgs/myphoto.jpg', None, None)
        algn, atts, url, title, href = match.groups()
        atts  = self.pba(atts)
        if algn:
            atts = atts + ' align="%s"' % self.iAlign(algn)

        if title:
            atts = atts + ' title="%s" alt="%s"' % (title, title)
        else:
            atts = atts + ' alt=""'

        # TODO how to do this in python?
        # size = @getimagesize(url)
        # if (size) atts .= " size[3]"

        if href:
            href = self.checkRefs(href)

        url = self.checkRefs(url)
        url = self.relURL(url)

        out = []
        if href: out.append('<a href="%s">' % href)
        out.append('<img src="%s"%s />' % (url, atts))
        if href: out.append('</a>')

        return ''.join(out)

    def code(self, text):
        text = self.doSpecial(text, '<code>', '</code>', self.fCode)
        text = self.doSpecial(text, '@', '@', self.fCode)
        text = self.doSpecial(text, '<pre>', '</pre>', self.fPre)
        return text

    def fCode(self, match):
        before, text, after = match.groups()
        if after == None: after = ''
        # text needs to be escaped
        if not self.restricted:
            text = self.encode_html(text)
        return ''.join([before, self.shelve('<code>%s</code>' % text), after])

    def fPre(self, match):
        before, text, after = match.groups()
        if after == None: after = ''
        # text needs to be escapedd
        if not self.restricted:
            text = self.encode_html(text)
        return ''.join([before, '<pre>', self.shelve(text), '</pre>', after])

    def doSpecial(self, text, start, end, method=None):
        if method == None:
            method = self.fSpecial
        pattern = re.compile(r'(^|\s|[\[({>])%s(.*?)%s(\s|$|[\])}])?' % (re.escape(start), re.escape(end)), re.M|re.S)
        return pattern.sub(method, text)

    def fSpecial(self, match):
        """
        special blocks like notextile or code
        """
        before, text, after = match.groups()
        if after == None: after = ''
        return ''.join([before, self.shelve(self.encode_html(text)), after])

    def noTextile(self, text):
        text = self.doSpecial(text, '<notextile>', '</notextile>', self.fTextile)
        return self.doSpecial(text, '==', '==', self.fTextile)

    def fTextile(self, match):
        before, notextile, after = match.groups()
        if after == None: after = ''
        return ''.join([before, self.shelve(notextile), after])


def textile(text, **args):
    """
    this function takes additional parameters:
    encoding - input encoding (default: 'utf-8')
    output - output encoding (default: 'utf-8')
    validate - perform mxTidy or uTidyLib validation (default: False)
    sanitize - sanitize output good for weblog comments (default: False)
    head_offset - ignored
    """
    return Textile().textile(text, **args)

def _test():
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    import sys
    if len(sys.argv) == 2:
        f = open(sys.argv[1])
        text = ''.join(f.readlines())
        print Textile().textile(text)
    else:
        _test()
