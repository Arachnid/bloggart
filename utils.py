import os
import re
import unicodedata

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

import config


def slugify(s):
  s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore')
  return re.sub('[^a-zA-Z0-9-]+', '-', s).strip('-')


def format_post_path(post, num):
  slug = slugify(post.title)
  if num > 0:
    slug += "-" + str(num)
  return config.post_path_format % {
      'slug': slug,
      'year': post.published.year,
      'month': post.published.month,
      'day': post.published.day,
  }


def render_template(template_name, template_vals=None, theme=None):
  template_vals.update({
      'config': config,
  })
  template_path = os.path.join("themes", theme or config.theme, template_name)
  return template.render(template_path, template_vals or {})
