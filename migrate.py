import itertools
import logging
import urllib
from django.utils import simplejson
from django.utils import html
from google.appengine.api import urlfetch
from google.appengine.ext import db
from google.appengine.ext import deferred

import config
import fix_path
import handlers
import models


def disqus_request(method, request_type=urlfetch.GET, **kwargs):
  kwargs['api_version'] = '1.1'
  if request_type == urlfetch.GET:
    url = "http://disqus.com/api/%s?%s" % (method, urllib.urlencode(kwargs))
    payload = None
  else:
    url = "http://disqus.com/api/%s/" % (method,)
    payload = urllib.urlencode(kwargs)
  response = urlfetch.fetch(url, payload, method=request_type)
  if response.status_code != 200:
    raise Exception("Invalid status code", response.status_code, response.content)
  result = simplejson.loads(response.content)
  if not result['succeeded']:
    raise Exception("RPC did not succeed", result)
  return result
  

class BloogBreakingMigration(object):
  class Article(db.Model):
    title = db.StringProperty()
    article_type = db.StringProperty()
    html = db.TextProperty()
    published = db.DateTimeProperty()
    updated = db.DateTimeProperty()
    tags = db.StringListProperty()

  class Comment(db.Model):
    name = db.StringProperty()
    email = db.StringProperty()
    homepage = db.StringProperty()
    body = db.TextProperty()
    published = db.DateTimeProperty()

  def __init__(self, disqus_user_key, disqus_forum_name):
    forums = disqus_request('get_forum_list', user_api_key=disqus_user_key)
    for forum in forums['message']:
      if forum['shortname'] == disqus_forum_name:
        forum_id = forum['id']
        break
    else:
      raise Exception("Forum not found", disqus_forum_name)
    self.forum_key = disqus_request(
        'get_forum_api_key',
        user_api_key=disqus_user_key,
        forum_id=forum_id)['message']

  def migrate_one_comment(self, thread_id, comment_key, replies, parent_id=None):
    comment = BloogBreakingMigration.Comment.get(comment_key)
    post_args = {
        'request_type': urlfetch.POST,
        'thread_id': thread_id,
        'message': html.strip_tags(comment.body).encode('utf-8'),
        'author_name': comment.name.encode('utf-8') if comment.name else 'Someone',
        'author_email': comment.email.encode('utf-8') if comment.email else 'nobody@notdot.net',
        'forum_api_key': self.forum_key,
        'created_at': comment.published.strftime('%Y-%m-%dT%H:%M'),
    }
    if comment.homepage:
      post_args['author_url'] = comment.homepage.encode('utf-8')
    if parent_id:
      post_args['parent_post'] = parent_id
    post_id = disqus_request('create_post', **post_args)['message']['id']
    for parent_id, replies in itertools.groupby(replies, lambda x:x[0]):
      parent_key = db.Key.from_path('Comment', parent_id, parent=comment_key)
      deferred.defer(self.migrate_one_comment, thread_id, parent_key,
                     [x[1:] for x in replies if x[1:]], post_id)

  def migrate_all_comments(self, article_key, title):
    thread_id = disqus_request(
        'thread_by_identifier',
        request_type=urlfetch.POST,
        identifier=str(article_key),
        forum_api_key=self.forum_key,
        title=title)['message']['thread']['id']
    disqus_request(
        'update_thread',
        request_type=urlfetch.POST,
        forum_api_key=self.forum_key,
        thread_id=thread_id,
        url="http://%s%s" % (config.host, article_key.name()))
    q = BloogBreakingMigration.Comment.all(keys_only=True)
    q.ancestor(article_key)
    # Get a list of IDs of comments
    comment_ids = sorted(tuple(x.to_path()[3::2]) for x in q.fetch(1000))
    # For each set of comments with the same parent
    for parent_id, replies in itertools.groupby(comment_ids, lambda x:x[0]):
      # Migrate that comment, passing in its child IDs
      parent_key = db.Key.from_path('Comment', parent_id, parent=article_key)
      deferred.defer(self.migrate_one_comment, thread_id, parent_key,
                     [x[1:] for x in replies if x[1:]])

  def migrate_one(self, article):
    post = models.BlogPost(
        path=article.key().name(),
        title=article.title,
        body=article.html,
        tags=set(article.tags),
        published=article.published,
        updated=article.updated,
        deps={})
    post.put()
    deferred.defer(self.migrate_all_comments, article.key(), article.title)
  
  def migrate_all(self, batch_size=20, start_key=None):
    q = BloogBreakingMigration.Article.all()
    if start_key:
      q.filter('__key__ >', start_key)
    articles = q.fetch(batch_size)
    for article in articles:
      self.migrate_one(article)
    if len(articles) == batch_size:
      deferred.defer(self.migrate_all, batch_size, articles[-1].key())
    else:
      logging.warn("Migration finished; starting rebuild.")
      regen = handlers.PostRegenerator()
      deferred.defer(regen.regenerate)
