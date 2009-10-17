import aetycoon
import re
from django.utils import text
from google.appengine.ext import db
from google.appengine.ext import deferred

import config
import generators
import static
import utils


class BlogPost(db.Model):
  # The URL path to the blog post. Posts have a path iff they are published.
  path = db.StringProperty()
  title = db.StringProperty(required=True, indexed=False)
  body = db.TextProperty(required=True)
  tags = aetycoon.SetProperty(basestring, indexed=False)
  published = db.DateTimeProperty(auto_now_add=True)
  updated = db.DateTimeProperty(auto_now=True)
  deps = aetycoon.PickleProperty()

  @aetycoon.TransformProperty(tags)
  def normalized_tags(tags):
    return list(set(utils.slugify(x.lower()) for x in tags))

  @property
  def summary(self):
    """Returns a summary of the blog post."""
    match = re.search("<!--.*cut.*-->", self.body)
    if match:
      return self.body[:match.start(0)]
    else:
      return text.truncate_html_words(self.body, config.summary_length)

  def publish(self):
    if not self.path:
      num = 0
      content = None
      while not content:
        path = utils.format_post_path(self, num)
        content = static.add(path, '', config.html_mime_type)
        num += 1
      self.path = path
    if not self.deps:
      self.deps = {}
    self.put()
    for generator_class in generators.generator_list:
      new_deps = set(generator_class.get_resource_list(self))
      new_etag = generator_class.get_etag(self)
      old_deps, old_etag = self.deps.get(generator_class.name(), (set(), None))
      if new_etag != old_etag:
        # If the etag has changed, regenerate everything
        to_regenerate = new_deps | old_deps
      else:
        # Otherwise just regenerate the changes
        to_regenerate = new_deps ^ old_deps
      if generator_class.can_defer:
        for dep in to_regenerate:
          deferred.defer(generator_class.generate_resource, None, dep)
      else:
        for dep in to_regenerate:
          generator_class.generate_resource(self, dep)
      self.deps[generator_class.name()] = (new_deps, new_etag)
    self.put()


class VersionInfo(db.Model):
  bloggart_major = db.IntegerProperty(required=True)
  bloggart_minor = db.IntegerProperty(required=True)
  bloggart_rev = db.IntegerProperty(required=True)

  @property
  def bloggart_version(self):
    return (self.bloggart_major, self.bloggart_minor, self.bloggart_rev)
