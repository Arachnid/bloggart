import os

from google.appengine.ext import webapp

import models
import utils

from django import newforms as forms
from google.appengine.ext.db import djangoforms


class PostForm(djangoforms.ModelForm):
  class Meta:
    model = models.BlogPost
    exclude = [ 'path', 'published', 'updated', 'deps' ]


def with_post(fun):
  def decorate(self, post_id=None):
    post = None
    if post_id:
      post = models.BlogPost.get_by_id(int(post_id))
      if not post:
        self.error(404)
        return
    fun(self, post)
  return decorate


class BaseHandler(webapp.RequestHandler):
  def render_to_response(self, template_name, template_vals=None, theme=None):
    template_name = os.path.join("admin", template_name)
    self.response.out.write(utils.render_template(template_name, template_vals,
                                                  theme))


class AdminHandler(BaseHandler):
  def get(self):
    offset = int(self.request.get('start', 0))
    count = int(self.request.get('count', 20))
    posts = models.BlogPost.all().order('-published').fetch(count, offset)
    template_vals = {
        'offset': offset,
        'count': count,
        'last_post': offset + len(posts) - 1,
        'prev_offset': max(0, offset - count),
        'next_offset': offset + count,
        'posts': posts,
    }
    self.render_to_response("index.html", template_vals)


class PostHandler(BaseHandler):
  def render_form(self, form):
    self.render_to_response("edit.html", {'form': form})

  @with_post
  def get(self, post):
    self.render_form(PostForm(instance=post))

  @with_post
  def post(self, post):
    form = PostForm(data=self.request.POST, instance=post)
    if form.is_valid():
      post = form.save(commit=False)
      post.publish()
      self.render_to_response("published.html", {'post': post})
    else:
      self.render_form(form)
