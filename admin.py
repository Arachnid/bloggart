from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

import fix_path
import post_deploy
import handlers


post_deploy.run_deploy_task()


application = webapp.WSGIApplication([
  ('/admin/', handlers.AdminHandler),
  ('/admin/newpost', handlers.PostHandler),
  ('/admin/post/(\d+)', handlers.PostHandler),
])


def main():
  run_wsgi_app(application)


if __name__ == '__main__':
  main()
