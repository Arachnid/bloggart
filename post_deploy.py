import datetime
import logging
import os
from google.appengine.api.labs import taskqueue
from google.appengine.ext import deferred

import config
import models
import static
import utils


BLOGGART_VERSION = (1, 0, 1)


class PostRegenerator(object):
  def __init__(self):
    self.seen = set()

  def regenerate(self, batch_size=50, start_ts=None):
    q = models.BlogPost.all().order('-published')
    q.filter('published <', start_ts or datetime.datetime.max)
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
      deferred.defer(self.regenerate, batch_size, posts[-1].published)


post_deploy_tasks = []


def generate_static_pages(pages):
  def generate(previous_version):
    for path, template, indexed in pages:
      rendered = utils.render_template(template)
      static.set(path, rendered, config.html_mime_type, indexed)
  return generate

post_deploy_tasks.append(generate_static_pages([
    ('/search', 'search.html', True),
    ('/cse.xml', 'cse.xml', False),
    ('/robots.txt', 'robots.txt', False),
]))


def regenerate_all(previous_version):
  if previous_version:
    ver_tuple = (
      previous_version.bloggart_major,
      previous_version.bloggart_minor,
      previous_version.bloggart_rev,
    )
  if ver_tuple < BLOGGART_VERSION:
    regen = PostRegenerator()
    deferred.defer(regen.regenerate)

post_deploy_tasks.append(regenerate_all)


def site_verification(previous_version):
  static.set('/' + config.google_site_verification,
             utils.render_template('site_verification.html'),
             config.html_mime_type, False)

if config.google_site_verification:
  post_deploy_tasks.append(site_verification)


def run_deploy_task():
  """Attempts to run the per-version deploy task."""
  task_name = 'deploy-%s' % os.environ['CURRENT_VERSION_ID'].replace('.', '-')
  try:
    deferred.defer(try_post_deploy, _name=task_name, _countdown=10)
  except (taskqueue.TaskAlreadyExistsError, taskqueue.TombstonedTaskError), e:
    pass


def try_post_deploy():
  """Runs post_deploy() iff it has not been run for this version yet."""
  version_info = models.VersionInfo.get_by_key_name(
      os.environ['CURRENT_VERSION_ID'])
  if not version_info:
    q = models.VersionInfo.all()
    q.order('-bloggart_major')
    q.order('-bloggart_minor')
    q.order('-bloggart_rev')
    post_deploy(q.get())


def post_deploy(previous_version):
  """Carries out post-deploy functions, such as rendering static pages."""
  for task in post_deploy_tasks:
    task(previous_version)

  new_version = models.VersionInfo(
      key_name=os.environ['CURRENT_VERSION_ID'],
      bloggart_major = BLOGGART_VERSION[0],
      bloggart_minor = BLOGGART_VERSION[1],
      bloggart_rev = BLOGGART_VERSION[2])
  new_version.put()
