import datetime
import hashlib

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import fix_path
import aetycoon


HTTP_DATE_FMT = "%a, %d %b %Y %H:%M:%S GMT"


class StaticContent(db.Model):
  """Container for statically served content.
  
  The serving path for content is provided in the key name.
  """
  body = db.BlobProperty(required=True)
  content_type = db.StringProperty(required=True)
  last_modified = db.DateTimeProperty(required=True, auto_now=True)
  etag = aetycoon.DerivedProperty(lambda x: hashlib.sha1(x.body).hexdigest())


def get(path):
  """Returns the StaticContent object for the provided path.
  
  Args:
    path: The path to retrieve StaticContent for.
  Returns:
    A StaticContent object, or None if no content exists for this path.
  """
  return StaticContent.get_by_key_name(path)


def set(path, body, content_type, **kwargs):
  """Sets the StaticContent for the provided path.
  
  Args:
    path: The path to store the content against.
    body: The data to serve for that path.
    content_type: The MIME type to serve the content as.
    **kwargs: Additional arguments to be passed to the StaticContent constructor
  Returns:
    A StaticContent object.
  """
  content = StaticContent(
      key_name=path,
      body=body,
      content_type=content_type,
      **kwargs)
  content.put()
  return content

def add(path, body, content_type, **kwargs):
  """Adds a new StaticContent and returns it.
  
  Args:
    As per set().
  Returns:
    A StaticContent object, or None if one already exists at the given path.
  """
  def _tx():
    if StaticContent.get_by_key_name(path):
      return None
    return set(path, body, content_type, **kwargs)
  return db.run_in_transaction(_tx)

  
class StaticContentHandler(webapp.RequestHandler):
  def output_content(self, content, serve=True):
    self.response.headers['Content-Type'] = content.content_type
    last_modified = content.last_modified.strftime(HTTP_DATE_FMT)
    self.response.headers['Last-Modified'] = last_modified
    self.response.headers['ETag'] = content.etag
    if serve:
      self.response.out.write(content.body)
    else:
      self.response.set_status(304)
  
  def get(self, path):
    content = get(path)
    if not content:
      self.error(404)
      return

    serve = True
    if 'If-Modified-Since' in self.request.headers:
      last_seen = datetime.datetime.strptime(
          self.request.headers['If-Modified-Since'],
          HTTP_DATE_FMT)
      if last_seen >= content.last_modified.replace(microsecond=0):
        serve = False
    if 'If-None-Match' in self.request.headers:
      etags = [x.strip()
               for x in self.request.headers['If-None-Match'].split(',')]
      if content.etag in etags:
        serve = False
    self.output_content(content, serve)


application = webapp.WSGIApplication([('(/.*)', StaticContentHandler)])


def main():
  run_wsgi_app(application)


if __name__ == '__main__':
  main()
