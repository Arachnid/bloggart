import aetycoon
import hashlib
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
  published = db.DateTimeProperty()
  updated = db.DateTimeProperty(auto_now=True)
  deps = aetycoon.PickleProperty()

  @aetycoon.TransformProperty(tags)
  def normalized_tags(tags):
    return list(set(utils.slugify(x.lower()) for x in tags))

  @property
  def tag_pairs(self):
    return [(x, utils.slugify(x.lower())) for x in self.tags]

  @property
  def summary(self):
    """Returns a summary of the blog post."""
    match = re.search("<!--.*cut.*-->", self.body)
    if match:
      return self.body[:match.start(0)]
    else:
      return text.truncate_html_words(self.body, config.summary_length)

  @property
  def hash(self):
    val = (self.title, self.body, self.tags, self.published)
    return hashlib.sha1(str(val)).hexdigest()

  @property
  def summary_hash(self):
    val = (self.title, self.summary, self.tags, self.published)
    return hashlib.sha1(str(val)).hexdigest()
  
  def publish(self):
    if not self.path:
      num = 0
      content = None
      while not content:
        path = utils.format_post_path(self, num)
        content = static.add(path, '', config.html_mime_type)
        num += 1
      self.path = path
      self.put()
    if not self.deps:
      self.deps = {}
    for generator_class, deps in self.get_deps():
      for dep in deps:
        if generator_class.can_defer:
          deferred.defer(generator_class.generate_resource, None, dep)
        else:
          generator_class.generate_resource(self, dep)
    self.put()
  
  def get_deps(self, regenerate=False):
    for generator_class in generators.generator_list:
      new_deps = set(generator_class.get_resource_list(self))
      new_etag = generator_class.get_etag(self)
      old_deps, old_etag = self.deps.get(generator_class.name(), (set(), None))
      if new_etag != old_etag or regenerate:
        # If the etag has changed, regenerate everything
        to_regenerate = new_deps | old_deps
      else:
        # Otherwise just regenerate the changes
        to_regenerate = new_deps ^ old_deps
      self.deps[generator_class.name()] = (new_deps, new_etag)
      yield generator_class, to_regenerate


class VersionInfo(db.Model):
  bloggart_major = db.IntegerProperty(required=True)
  bloggart_minor = db.IntegerProperty(required=True)
  bloggart_rev = db.IntegerProperty(required=True)

  @property
  def bloggart_version(self):
    return (self.bloggart_major, self.bloggart_minor, self.bloggart_rev)
