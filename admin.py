from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from django import newforms as forms
from google.appengine.ext.db import djangoforms

import os
import re

import fix_path
import config
import static


def slugify(s):
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


def render_template(template_name, template_vals=None, theme=None):
  template_path = os.path.join("themes", theme or config.theme, template_name)
  return template.render(template_path, template_vals or {})


class BlogPost(db.Model):
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
    return render_template("post.html", template_vals)

  def publish(self):
    rendered = self.render()
    if not self.path:
      num = 0
      content = None
      while not content:
        path = format_post_path(self, num)
        content = static.add(path, rendered, "text/html")
        num += 1
      self.path = path
      self.put()
    else:
      static.set(self.path, rendered, "text/html")


class PostForm(djangoforms.ModelForm):
  class Meta:
    model = BlogPost
    exclude = [ 'path', 'published', 'updated' ]


class PostHandler(webapp.RequestHandler):
  def render_to_response(self, template_name, template_vals=None, theme=None):
    template_name = os.path.join("admin", template_name)
    self.response.out.write(render_template(template_name, template_vals,
                                            theme))

  def render_form(self, form):
    self.render_to_response("edit.html", {'form': form})

  def get(self):
    self.render_form(PostForm())

  def post(self):
    form = PostForm(data=self.request.POST)
    if form.is_valid():
      post = form.save(commit=False)
      post.publish()
      self.render_to_response("published.html", {'post': post})
    else:
      self.render_form(form)


application = webapp.WSGIApplication([
  ('/admin/newpost', PostHandler),
])


def main():
  run_wsgi_app(application)


if __name__ == '__main__':
  main()
