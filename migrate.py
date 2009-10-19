import logging
from google.appengine.ext import db
from google.appengine.ext import deferred

import fix_path
import handlers
import models


class BloogMigration(object):
  class Article(db.Model):
    title = db.StringProperty()
    article_type = db.StringProperty()
    html = db.TextProperty()
    published = db.DateTimeProperty()
    updated = db.DateTimeProperty()
    tags = db.StringListProperty()

  @classmethod
  def migrate_one_breaking(cls, post_key):
    logging.debug("Migrating post with key %s", post_key)
    article = cls.Article.get(post_key)
    post = models.BlogPost(
        path=article.key().name(),
        title=article.title,
        body=article.html,
        tags=set(article.tags),
        published=article.published,
        updated=article.updated,
        deps={})
    post.put()
  
  @classmethod
  def migrate_all_breaking(cls, batch_size=20, start_key=None):
    q = cls.Article.all(keys_only=True)
    if start_key:
      q.filter('__key__ >', start_key)
    articles = q.fetch(batch_size)
    for key in articles:
      cls.migrate_one_breaking(key)
    if len(articles) == batch_size:
      deferred.defer(cls.migrate_all_breaking, batch_size, articles[-1])
    else:
      logging.warn("Migration finished; starting rebuild.")
      regen = handlers.PostRegenerator()
      deferred.defer(regen.regenerate)
