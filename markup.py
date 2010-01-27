"""
Support for different markup languages for the body of a post.

The following markup languages are supported:
 - HTML
 - Plain text
 - ReStructured Text
 - Markdown
 - Textile

For ReStructuredText and Markdown syntax highlighting of source code is
available.
"""

# TODO: Add summary rendering.
# TODO: Docstrings.

import logging
import re
from cStringIO import StringIO

from django.utils import html
from django.utils import text

import config
import utils

# Fix sys.path
import fix_path
fix_path.fix_sys_path()

# Import markup module from lib/
import markdown
import markdown_processor
import rst_directive
import textile
from docutils.core import publish_parts


CUT_SEPARATOR_REGEX = r'<!--.*cut.*-->'


def render_rst(content):
  warning_stream = StringIO()
  parts = publish_parts(content, writer_name='html4css1',
                        settings_overrides={
                          '_disable_config': True,
                          'embed_stylesheet': False,
                          'warning_stream': warning_stream,
                          'report_level': 2,
                        })
  rst_warnings = warning_stream.getvalue()
  if rst_warnings:
      logging.warn(rst_warnings)
  return parts['html_body']


def render_markdown(content):
  md = markdown.Markdown()
  md.textPreprocessors.insert(0, markdown_processor.CodeBlockPreprocessor())
  return md.convert(content)


def render_textile(content):
  return textile.textile(content.encode('utf-8'))


# Mapping: string ID -> (human readable name, renderer)
MARKUP_MAP = {
    'html':     ('HTML', lambda c: c),
    'txt':      ('Plain Text', lambda c: html.linebreaks(html.escape(c))),
    'markdown': ('Markdown', render_markdown),
    'textile':  ('Textile', render_textile),
    'rst':      ('ReStructuredText', render_rst),
}


def get_renderer(post):
  """Returns a render function for this posts body markup."""
  return MARKUP_MAP.get(post.body_markup)[1]


def clean_content(content):
  """Clean up the raw body.

  Actually this removes the cut separator.
  """
  return re.sub(CUT_SEPARATOR_REGEX, '', content)


def render_body(post):
  """Return the post's body rendered to HTML."""
  renderer = get_renderer(post)
  return renderer(clean_content(post.body))


def render_summary(post):
  """Return the post's summary rendered to HTML."""
  renderer = get_renderer(post)
  match = re.search(CUT_SEPARATOR_REGEX, post.body)
  if match:
    return renderer(post.body[:match.start(0)])
  else:
    return text.truncate_html_words(renderer(clean_content(post.body)),
                                    config.summary_length)
