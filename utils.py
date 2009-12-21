import os
import re
import unicodedata

from google.appengine.ext import webapp
from google.appengine.ext.webapp.template import _swap_settings

import django.conf
from django import template
from django.template import loader

import config

BASE_DIR = os.path.dirname(__file__)

if isinstance(config.theme, (list, tuple)):
  TEMPLATE_DIRS = config.theme
else:
  TEMPLATE_DIRS = [os.path.abspath(os.path.join(BASE_DIR, 'themes/default'))]
  if config.theme and config.theme != 'default':
    TEMPLATE_DIRS.insert(0,
                         os.path.abspath(os.path.join(BASE_DIR, 'themes', config.theme)))


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


def get_template_vals_defaults(template_vals=None):
  if template_vals is None:
    template_vals = {}
  template_vals.update({
      'config': config,
      'devel': os.environ['SERVER_SOFTWARE'].startswith('Devel'),
  })
  return template_vals


def render_template(template_name, template_vals=None, theme=None):
  template_vals = get_template_vals_defaults(template_vals)
  template_vals.update({'template_name': template_name})
  old_settings = _swap_settings({'TEMPLATE_DIRS': TEMPLATE_DIRS})
  try:
    tpl = loader.get_template(template_name)
    rendered = tpl.render(template.Context(template_vals))
  finally:
    _swap_settings(old_settings)
  return rendered


def _get_all_paths():
  import static
  keys = []
  q = static.StaticContent.all(keys_only=True).filter('indexed', True)
  cur = q.fetch(1000)
  while len(cur) == 1000:
    keys.extend(cur)
    q = static.StaticContent.all(keys_only=True)
    q.filter('indexed', True)
    q.filter('__key__ >', cur[-1])
    cur = q.fetch(1000)
  keys.extend(cur)
  return [x.name() for x in keys]


def _regenerate_sitemap():
  import static
  paths = _get_all_paths()
  rendered = render_template('sitemap.xml', {'paths': paths})
  static.set('/sitemap.xml', rendered, 'application/xml', False)
