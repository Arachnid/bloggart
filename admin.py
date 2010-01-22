from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

import fix_path
import config
import post_deploy
import handlers


post_deploy.run_deploy_task()


application = webapp.WSGIApplication([
  (config.url_prefix + '/admin/', handlers.AdminHandler),
  (config.url_prefix + '/admin/newpost', handlers.PostHandler),
  (config.url_prefix + '/admin/post/(\d+)', handlers.PostHandler),
  (config.url_prefix + '/admin/regenerate', handlers.RegenerateHandler),
])


def main():
  fix_path.fix_sys_path()
  run_wsgi_app(application)


if __name__ == '__main__':
  main()
