import datetime
import hashlib

from google.appengine.api import memcache
from google.appengine.api import taskqueue
from google.appengine.ext import db
from google.appengine.ext import deferred
from google.appengine.datastore import entity_pb
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import fix_path
import aetycoon
import config
import utils


HTTP_DATE_FMT = "%a, %d %b %Y %H:%M:%S GMT"

if config.google_site_verification is not None:
    ROOT_ONLY_FILES = ['/robots.txt','/' + config.google_site_verification]
else:
    ROOT_ONLY_FILES = ['/robots.txt']

class StaticContent(db.Model):
  """Container for statically served content.

  The serving path for content is provided in the key name.
  """
  body = db.BlobProperty()
  content_type = db.StringProperty()
  status = db.IntegerProperty(required=True, default=200)
  last_modified = db.DateTimeProperty(required=True)
  etag = aetycoon.DerivedProperty(lambda x: hashlib.sha1(x.body).hexdigest())
  indexed = db.BooleanProperty(required=True, default=True)
  headers = db.StringListProperty()


def get(path):
  """Returns the StaticContent object for the provided path.

  Args:
    path: The path to retrieve StaticContent for.
  Returns:
    A StaticContent object, or None if no content exists for this path.
  """
  entity = memcache.get(path)
  if entity:
    entity = db.model_from_protobuf(entity_pb.EntityProto(entity))
  else:
    entity = StaticContent.get_by_key_name(path)
    if entity:
      memcache.set(path, db.model_to_protobuf(entity).Encode())

  return entity


def set(path, body, content_type, indexed=True, **kwargs):
  """Sets the StaticContent for the provided path.

  Args:
    path: The path to store the content against.
    body: The data to serve for that path.
    content_type: The MIME type to serve the content as.
    indexed: Index this page in the sitemap?
    **kwargs: Additional arguments to be passed to the StaticContent constructor
  Returns:
    A StaticContent object.
  """
  now = datetime.datetime.now().replace(second=0, microsecond=0)
  defaults = {
    "last_modified": now,
  }
  defaults.update(kwargs)
  content = StaticContent(
      key_name=path,
      body=body,
      content_type=content_type,
      indexed=indexed,
      **defaults)
  content.put()
  memcache.replace(path, db.model_to_protobuf(content).Encode())
  try:
    eta = now.replace(second=0, microsecond=0) + datetime.timedelta(seconds=65)
    if indexed:
      deferred.defer(
          utils._regenerate_sitemap,
          _name='sitemap-%s' % (now.strftime('%Y%m%d%H%M'),),
          _eta=eta)
  except (taskqueue.taskqueue.TaskAlreadyExistsError, taskqueue.taskqueue.TombstonedTaskError), e:
    pass
  return content

def add(path, body, content_type, indexed=True, **kwargs):
  """Adds a new StaticContent and returns it.

  Args:
    As per set().
  Returns:
    A StaticContent object, or None if one already exists at the given path.
  """
  def _tx():
    if StaticContent.get_by_key_name(path):
      return None
    return set(path, body, content_type, indexed, **kwargs)
  return db.run_in_transaction(_tx)

def remove(path):
  """Deletes a StaticContent.

  Args:
    path: Path of the static content to be removed.
  """
  memcache.delete(path)
  def _tx():
    content = StaticContent.get_by_key_name(path)
    if not content:
      return
    content.delete()
  return db.run_in_transaction(_tx)

class StaticContentHandler(webapp.RequestHandler):
  def output_content(self, content, serve=True):
    if content.content_type:
      self.response.headers['Content-Type'] = content.content_type
    last_modified = content.last_modified.strftime(HTTP_DATE_FMT)
    self.response.headers['Last-Modified'] = last_modified
    self.response.headers['ETag'] = '"%s"' % (content.etag,)
    for header in content.headers:
      key, value = header.split(':', 1)
      self.response.headers[key] = value.strip()
    if serve:
      self.response.set_status(content.status)
      self.response.out.write(content.body)
    else:
      self.response.set_status(304)

  def get(self, path):
    if not path.startswith(config.url_prefix):
      if path not in ROOT_ONLY_FILES:
        self.error(404)
        self.response.out.write(utils.render_template('404.html'))
        return
    else:
      if config.url_prefix != '':
        path = path[len(config.url_prefix):]# Strip off prefix
        if path in ROOT_ONLY_FILES:# This lives at root
          self.error(404)
          self.response.out.write(utils.render_template('404.html'))
          return
    content = get(path)
    if not content:
      self.error(404)
      self.response.out.write(utils.render_template('404.html'))
      return

    serve = True
    if 'If-Modified-Since' in self.request.headers:
      try:
        last_seen = datetime.datetime.strptime(
            self.request.headers['If-Modified-Since'].split(';')[0],# IE8 '; length=XXXX' as extra arg bug
            HTTP_DATE_FMT)
        if last_seen >= content.last_modified.replace(microsecond=0):
          serve = False
      except ValueError, e:
        import logging
        logging.error('StaticContentHandler in static.py, ValueError:' + self.request.headers['If-Modified-Since'])
    if 'If-None-Match' in self.request.headers:
      etags = [x.strip('" ')
               for x in self.request.headers['If-None-Match'].split(',')]
      if content.etag in etags:
        serve = False
    self.output_content(content, serve)


application = webapp.WSGIApplication([
                ('(/.*)', StaticContentHandler),
              ])


def main():
  fix_path.fix_sys_path()
  run_wsgi_app(application)


if __name__ == '__main__':
  main()
