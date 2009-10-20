import os
from google.appengine.api.labs import taskqueue
from google.appengine.ext import deferred

import config
import models
import static
import utils


BLOGGART_VERSION = (1, 0, 0)


post_deploy_tasks = []


def generate_static_pages(pages):
  def generate(previous_version):
    for path, template in pages:
      rendered = utils.render_template(template)
      static.set(path, rendered, config.html_mime_type)
  return generate

post_deploy_tasks.append(generate_static_pages([
    ('/search', 'search.html'),
    ('/cse.xml', 'cse.xml'),
]))


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
