from google.appengine.ext import db

import config
import static
import utils


class BlogPost(db.Model):
  MIME_TYPE = "text/html; charset=utf-8"

  # The URL path to the blog post. Posts have a path iff they are published.
  path = db.StringProperty()
  title = db.StringProperty(required=True, indexed=False)
  body = db.TextProperty(required=True)
  published = db.DateTimeProperty(auto_now_add=True)
  updated = db.DateTimeProperty(auto_now=True)

  def render(self):
    template_vals = {
        'config': config,
        'post': self,
    }
    return utils.render_template("post.html", template_vals)

  def publish(self):
    rendered = self.render()
    if not self.path:
      num = 0
      content = None
      while not content:
        path = utils.format_post_path(self, num)
        content = static.add(path, rendered, self.MIME_TYPE)
        num += 1
      self.path = path
      self.put()
    else:
      static.set(self.path, rendered, self.MIME_TYPE)
