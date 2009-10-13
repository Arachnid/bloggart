import hashlib
import os
from google.appengine.ext import db
from google.appengine.ext import deferred

import fix_path
import config
import static
import utils


generator_list = []


class ContentGenerator(object):
  """A class that generates content and dependency lists for blog posts."""

  can_defer = True
  """If True, this ContentGenerator's resources can be generated later."""

  @classmethod
  def name(cls):
    return cls.__name__

  @classmethod
  def get_resource_list(cls, post):
    """Returns a list of resources for the given post.
    
    Args:
      post: A BlogPost entity.
    Returns:
      A list of resource strings representing resources affected by this post.
    """
    raise NotImplementedError()

  @classmethod
  def get_etag(cls, post):
    """Returns a string that changes if the resource requires regenerating.
    
    Args:
      post: A BlogPost entity.
    Returns:
      A string representing the current state of the entity, as relevant to this
      ContentGenerator.
    """
    raise NotImplementedError()

  @classmethod
  def generate_resource(cls, post, resource):
    """(Re)generates a resource for the provided post.
    
    Args:
      post: A BlogPost entity.
      resource: A resource string as returned by get_resource_list.
    """
    raise NotImplementedError()


class PostContentGenerator(ContentGenerator):
  """ContentGenerator for the actual blog post itself."""
  
  can_defer = False
  
  @classmethod
  def get_resource_list(cls, post):
    return [post.key().id()]

  @classmethod
  def get_etag(cls, post):
    return hashlib.sha1(db.model_to_protobuf(post).Encode()).hexdigest()

  @classmethod
  def generate_resource(cls, post, resource):
    import models
    if not post:
      post = models.BlogPost.get_by_id(resource)
    else:
      assert resource == post.key().id()
    template_vals = {
        'post': post,
    }
    rendered = utils.render_template("post.html", template_vals)
    static.set(post.path, rendered, config.html_mime_type)
generator_list.append(PostContentGenerator)


class IndexContentGenerator(ContentGenerator):
  """ContentGenerator for the homepage of the blog and archive pages."""

  @classmethod
  def get_resource_list(cls, post):
    return ["index"]

  @classmethod
  def get_etag(cls, post):
    return hashlib.sha1((post.title + post.summary).encode('utf-8')).hexdigest()

  @classmethod
  def generate_resource(cls, post, resource, pagenum=1, start_ts=None):
    import models
    q = models.BlogPost.all().order('-published')
    if start_ts:
      q.filter('published <=', start_ts)

    posts = q.fetch(config.posts_per_page + 1)
    more_posts = len(posts) > config.posts_per_page

    template_vals = {
        'posts': posts[:config.posts_per_page],
        'prev_page': "/page/%d" % (pagenum - 1,) if pagenum > 1 else None,
        'next_page': "/page/%d" % (pagenum + 1,) if more_posts else None,
    }
    rendered = utils.render_template("listing.html", template_vals)

    path_args = {
        'resource': resource,
        'pagenum': pagenum,
    }
    static.set('/page/%d' % (pagenum,), rendered, config.html_mime_type)
    if pagenum == 1:
      static.set('/', rendered, config.html_mime_type)

    if more_posts:
      deferred.defer(cls.generate_resource, None, resource, pagenum + 1,
                     posts[-1].published)
generator_list.append(IndexContentGenerator)


class AtomContentGenerator(ContentGenerator):
  """ContentGenerator for Atom feeds."""
  
  @classmethod
  def get_resource_list(cls, post):
    return ["atom"]

  @classmethod
  def get_etag(cls, post):
    return hashlib.sha1(db.model_to_protobuf(post).Encode()).hexdigest()

  @classmethod
  def generate_resource(cls, post, resource):
    import models
    q = models.BlogPost.all().order('-updated')
    posts = q.fetch(10)
    template_vals = {
        'posts': posts,
    }
    rendered = utils.render_template("atom.xml", template_vals)
    static.set('/feeds/atom.xml', rendered,
               'application/atom+xml; charset=utf-8')
generator_list.append(AtomContentGenerator)
