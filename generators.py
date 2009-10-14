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


class ListingContentGenerator(ContentGenerator):
  path = None
  """The path for listing pages."""

  first_page_path = None
  """The path for the first listing page."""

  @classmethod
  def get_etag(cls, post):
    return hashlib.sha1((post.title + post.summary).encode('utf-8')).hexdigest()

  @classmethod
  def _filter_query(cls, resource, q):
    """Applies filters to the BlogPost query.
    
    Args:
      resource: The resource being generated.
      q: The query to act on.
    """
    pass

  @classmethod
  def generate_resource(cls, post, resource, pagenum=1, start_ts=None):
    import models
    q = models.BlogPost.all().order('-published')
    if start_ts:
      q.filter('published <=', start_ts)
    cls._filter_query(resource, q)

    posts = q.fetch(config.posts_per_page + 1)
    more_posts = len(posts) > config.posts_per_page

    path_args = {
        'resource': resource,
    }
    path_args['pagenum'] = pagenum - 1
    prev_page = cls.path % path_args
    path_args['pagenum'] = pagenum + 1
    next_page = cls.path % path_args
    template_vals = {
        'posts': posts[:config.posts_per_page],
        'prev_page': prev_page if pagenum > 1 else None,
        'next_page': next_page if more_posts else None,
    }
    rendered = utils.render_template("listing.html", template_vals)

    path_args['pagenum'] = pagenum
    static.set(cls.path % path_args, rendered, config.html_mime_type)
    if pagenum == 1:
      static.set(cls.first_page_path % path_args, rendered,
                 config.html_mime_type)

    if more_posts:
      deferred.defer(cls.generate_resource, None, resource, pagenum + 1,
                     posts[-1].published)


class IndexContentGenerator(ListingContentGenerator):
  """ContentGenerator for the homepage of the blog and archive pages."""

  path = '/page/%(pagenum)d'
  first_page_path = '/'

  @classmethod
  def get_resource_list(cls, post):
    return ["index"]
generator_list.append(IndexContentGenerator)


class TagsContentGenerator(ListingContentGenerator):
  """ContentGenerator for the tags pages."""

  path = '/tag/%(resource)s/%(pagenum)d'
  first_page_path = '/tag/%(resource)s'

  @classmethod
  def get_resource_list(cls, post):
    return post.tags

  @classmethod
  def _filter_query(cls, resource, q):
    q.filter('tags =', resource)
generator_list.append(TagsContentGenerator)


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
