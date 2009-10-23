import datetime
import logging
import os

from google.appengine.ext import deferred
from google.appengine.ext import webapp

import models
import post_deploy
import utils

from django import newforms as forms
from google.appengine.ext.db import djangoforms


class PostForm(djangoforms.ModelForm):
  title = forms.CharField(widget=forms.TextInput(attrs={'id':'name'}))
  body = forms.CharField(widget=forms.Textarea(attrs={
      'id':'message',
      'rows': 10,
      'cols': 20}))
  tags = forms.CharField(widget=forms.Textarea(attrs={'rows': 5, 'cols': 20}))
  draft = forms.BooleanField(required=False)
  class Meta:
    model = models.BlogPost
    fields = [ 'title', 'body', 'tags' ]


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
    if not template_vals:
      template_vals = {}
    template_vals.update({
        'path': self.request.path,
        'handler_class': self.__class__.__name__,
    })
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
    self.render_form(PostForm(
        instance=post,
        initial={'draft': post and post.published is None}))

  @with_post
  def post(self, post):
    form = PostForm(data=self.request.POST, instance=post,
                    initial={'draft': post and post.published is None})
    if form.is_valid():
      post = form.save(commit=False)
      if form.clean_data['draft']:
        post.put()
      else:
        post.published = post.published or datetime.datetime.now()
        post.publish()
      self.render_to_response("published.html", {
          'post': post,
          'draft': form.clean_data['draft']})
    else:
      self.render_form(form)


class PostRegenerator(object):
  def __init__(self):
    self.seen = set()

  def regenerate(self, batch_size=50, start_key=None):
    q = models.BlogPost.all()
    if start_key:
      q.filter('__key__ >', start_key)
    posts = q.fetch(batch_size)
    for post in posts:
      for generator_class, deps in post.get_deps(True):
        for dep in deps:
          if (generator_class.__name__, dep) not in self.seen:
            logging.warn((generator_class.__name__, dep))
            self.seen.add((generator_class.__name__, dep))
            deferred.defer(generator_class.generate_resource, None, dep)
      post.put()
    if len(posts) == batch_size:
      deferred.defer(self.regenerate, batch_size, posts[-1].key())


class RegenerateHandler(BaseHandler):
  def post(self):
    regen = PostRegenerator()
    deferred.defer(regen.regenerate)
    deferred.defer(post_deploy.post_deploy, post_deploy.BLOGGART_VERSION)
    self.render_to_response("regenerating.html")
