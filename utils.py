import os,cgi
import re
import unicodedata
import embedly
import logging

from google.appengine.ext import webapp
from google.appengine.ext.webapp.template import _swap_settings

import django.conf
from django import template
from django.template import loader

import config

BASE_DIR = os.path.dirname(__file__)

if isinstance(config.theme, (list, tuple)):
  TEMPLATE_DIRS = config.theme
else:
  TEMPLATE_DIRS = [os.path.abspath(os.path.join(BASE_DIR, 'themes/default'))]
  if config.theme and config.theme != 'default':
    TEMPLATE_DIRS.insert(0,
                         os.path.abspath(os.path.join(BASE_DIR, 'themes', config.theme)))

def oembed_replace(str='',ptype='post'):
     ns = str
     s = str
     oe = re.compile("\[http://(.*youtube\.com/watch.*|.*\.youtube\.com/v/.*|youtu\.be/.*|.*\.youtube\.com/user/.*#.*|.*\.youtube\.com/.*#.*/.*|.*justin\.tv/.*|.*justin\.tv/.*/b/.*|www\.ustream\.tv/recorded/.*|www\.ustream\.tv/channel/.*|qik\.com/video/.*|qik\.com/.*|.*revision3\.com/.*|.*\.dailymotion\.com/video/.*|.*\.dailymotion\.com/.*/video/.*|www\.collegehumor\.com/video:.*|.*twitvid\.com/.*|www\.break\.com/.*/.*|vids\.myspace\.com/index\.cfm\?fuseaction=vids\.individual&videoid.*|www\.myspace\.com/index\.cfm\?fuseaction=.*&videoid.*|www\.metacafe\.com/watch/.*|blip\.tv/file/.*|.*\.blip\.tv/file/.*|video\.google\.com/videoplay\?.*|.*revver\.com/video/.*|video\.yahoo\.com/watch/.*/.*|video\.yahoo\.com/network/.*|.*viddler\.com/explore/.*/videos/.*|liveleak\.com/view\?.*|www\.liveleak\.com/view\?.*|animoto\.com/play/.*|dotsub\.com/view/.*|www\.overstream\.net/view\.php\?oid=.*|www\.livestream\.com/.*|www\.worldstarhiphop\.com/videos/video.*\.php\?v=.*|worldstarhiphop\.com/videos/video.*\.php\?v=.*|teachertube\.com/viewVideo\.php.*|teachertube\.com/viewVideo\.php.*|bambuser\.com/v/.*|bambuser\.com/channel/.*|bambuser\.com/channel/.*/broadcast/.*|.*yfrog\..*/.*|tweetphoto\.com/.*|www\.flickr\.com/photos/.*|.*twitpic\.com/.*|.*imgur\.com/.*|.*\.posterous\.com/.*|post\.ly/.*|twitgoo\.com/.*|i.*\.photobucket\.com/albums/.*|gi.*\.photobucket\.com/groups/.*|phodroid\.com/.*/.*/.*|www\.mobypicture\.com/user/.*/view/.*|moby\.to/.*|xkcd\.com/.*|www\.xkcd\.com/.*|www\.asofterworld\.com/index\.php\?id=.*|www\.qwantz\.com/index\.php\?comic=.*|23hq\.com/.*/photo/.*|www\.23hq\.com/.*/photo/.*|.*dribbble\.com/shots/.*|drbl\.in/.*|.*\.smugmug\.com/.*|.*\.smugmug\.com/.*#.*|emberapp\.com/.*/images/.*|emberapp\.com/.*/images/.*/sizes/.*|emberapp\.com/.*/collections/.*/.*|emberapp\.com/.*/categories/.*/.*/.*|embr\.it/.*|picasaweb\.google\.com.*/.*/.*#.*|picasaweb\.google\.com.*/lh/photo/.*|picasaweb\.google\.com.*/.*/.*|dailybooth\.com/.*/.*|brizzly\.com/pic/.*|pics\.brizzly\.com/.*\.jpg|img\.ly/.*|www\.facebook\.com/photo\.php.*|www\.tinypic\.com/view\.php.*|tinypic\.com/view\.php.*|www\.tinypic\.com/player\.php.*|tinypic\.com/player\.php.*|www\.tinypic\.com/r/.*/.*|tinypic\.com/r/.*/.*|.*\.tinypic\.com/.*\.jpg|.*\.tinypic\.com/.*\.png|meadd\.com/.*/.*|meadd\.com/.*|.*\.deviantart\.com/art/.*|.*\.deviantart\.com/gallery/.*|.*\.deviantart\.com/#/.*|fav\.me/.*|.*\.deviantart\.com|.*\.deviantart\.com/gallery|.*\.deviantart\.com/.*/.*\.jpg|.*\.deviantart\.com/.*/.*\.gif|.*\.deviantart\.net/.*/.*\.jpg|.*\.deviantart\.net/.*/.*\.gif|www\.whitehouse\.gov/photos-and-video/video/.*|www\.whitehouse\.gov/video/.*|wh\.gov/photos-and-video/video/.*|wh\.gov/video/.*|www\.hulu\.com/watch.*|www\.hulu\.com/w/.*|hulu\.com/watch.*|hulu\.com/w/.*|movieclips\.com/watch/.*/.*/|movieclips\.com/watch/.*/.*/.*/.*|.*crackle\.com/c/.*|www\.fancast\.com/.*/videos|www\.funnyordie\.com/videos/.*|www\.vimeo\.com/groups/.*/videos/.*|www\.vimeo\.com/.*|vimeo\.com/groups/.*/videos/.*|vimeo\.com/.*|www\.ted\.com/talks/.*\.html.*|www\.ted\.com/talks/lang/.*/.*\.html.*|www\.ted\.com/index\.php/talks/.*\.html.*|www\.ted\.com/index\.php/talks/lang/.*/.*\.html.*|.*omnisio\.com/.*|.*nfb\.ca/film/.*|www\.thedailyshow\.com/watch/.*|www\.thedailyshow\.com/full-episodes/.*|www\.thedailyshow\.com/collection/.*/.*/.*|movies\.yahoo\.com/movie/.*/video/.*|movies\.yahoo\.com/movie/.*/info|movies\.yahoo\.com/movie/.*/trailer|www\.colbertnation\.com/the-colbert-report-collections/.*|www\.colbertnation\.com/full-episodes/.*|www\.colbertnation\.com/the-colbert-report-videos/.*|www\.comedycentral\.com/videos/index\.jhtml\?.*|www\.theonion\.com/video/.*|theonion\.com/video/.*|wordpress\.tv/.*/.*/.*/.*/|www\.traileraddict\.com/trailer/.*|www\.traileraddict\.com/clip/.*|www\.traileraddict\.com/poster/.*|www\.escapistmagazine\.com/videos/.*|www\.trailerspy\.com/trailer/.*/.*|www\.trailerspy\.com/trailer/.*|www\.trailerspy\.com/view_video\.php.*|www\.atom\.com/.*/.*/|fora\.tv/.*/.*/.*/.*|www\.spike\.com/video/.*|www\.gametrailers\.com/video/.*|gametrailers\.com/video/.*|www\.koldcast\.tv/video/.*|www\.koldcast\.tv/#video:.*|www\.godtube\.com/featured/video/.*|www\.tangle\.com/view_video.*|soundcloud\.com/.*|soundcloud\.com/.*/.*|soundcloud\.com/.*/sets/.*|soundcloud\.com/groups/.*|www\\.last\\.fm/music/.*|www\\.last\\.fm/music/+videos/.*|www\\.last\\.fm/music/+images/.*|www\\.last\\.fm/music/.*/_/.*|www\\.last\\.fm/music/.*/.*|www\.mixcloud\.com/.*/.*/|espn\.go\.com/video/clip.*|espn\.go\.com/.*/story.*|cnbc\.com/id/.*|cbsnews\.com/video/watch/.*|www\.cnn\.com/video/.*|edition\.cnn\.com/video/.*|money\.cnn\.com/video/.*|today\.msnbc\.msn\.com/id/.*/vp/.*|www\.msnbc\.msn\.com/id/.*/vp/.*|www\.msnbc\.msn\.com/id/.*/ns/.*|today\.msnbc\.msn\.com/id/.*/ns/.*|multimedia\.foxsports\.com/m/video/.*/.*|msn\.foxsports\.com/video.*|.*amazon\..*/gp/product/.*|.*amazon\..*/.*/dp/.*|.*amazon\..*/dp/.*|.*amazon\..*/o/ASIN/.*|.*amazon\..*/gp/offer-listing/.*|.*amazon\..*/.*/ASIN/.*|.*amazon\..*/gp/product/images/.*|www\.amzn\.com/.*|amzn\.com/.*|www\.shopstyle\.com/browse.*|www\.shopstyle\.com/action/apiVisitRetailer.*|www\.shopstyle\.com/action/viewLook.*|gist\.github\.com/.*|twitter\.com/.*/status/.*|twitter\.com/.*/statuses/.*|www\.slideshare\.net/.*/.*|.*\.scribd\.com/doc/.*|screenr\.com/.*|polldaddy\.com/community/poll/.*|polldaddy\.com/poll/.*|answers\.polldaddy\.com/poll/.*|www\.5min\.com/Video/.*|www\.howcast\.com/videos/.*|www\.screencast\.com/.*/media/.*|screencast\.com/.*/media/.*|www\.screencast\.com/t/.*|screencast\.com/t/.*|issuu\.com/.*/docs/.*|www\.kickstarter\.com/projects/.*/.*|www\.scrapblog\.com/viewer/viewer\.aspx.*|my\.opera\.com/.*/albums/show\.dml\?id=.*|my\.opera\.com/.*/albums/showpic\.dml\?album=.*&picture=.*|tumblr\.com/.*|.*\.tumblr\.com/post/.*|www\.polleverywhere\.com/polls/.*|www\.polleverywhere\.com/multiple_choice_polls/.*|www\.polleverywhere\.com/free_text_polls/.*|.*\.status\.net/notice/.*|identi\.ca/notice/.*|shitmydadsays\.com/notice/.*)]", re.I)
     urls = oe.findall(s)
     if ptype == 'list':
         oembed_json = embedly.get_multi(urls,maxwidth=150)
     elif ptype == 'post' or ptype == 'atom':
         oembed_json = embedly.get_multi(urls,maxwidth=500)

     for idx,item in enumerate(oembed_json):
         try:
             title = item['title']
         except KeyError:
             title = ''
         try:
             url = item['url']
         except KeyError:
             url = ''
         try:
             thumbnail_url = item['thumbnail_url']
         except KeyError:
             thumbnail_url = ''
         r = ''
         if item['type'] == 'photo': 
             if ptype == 'post' or ptype == 'atom':
                 r = ' <a href="http://' + urls[idx] + '" target="_blank"><img src="' + url + '" alt="' + title + '"/></a>'
         if item['type'] == 'video':
             if ptype == 'post' or ptype == 'atom':
                 r = ' '+item['html']
         if item['type'] == 'rich':
             if ptype == 'post' or ptype == 'atom':
                 r = ' '+item['html']
         if item['type'] == 'link':
             if ptype == 'post' or ptype == 'atom':
                 r = ' <a href="' + url + '">' + title + '</a>'
         if ptype == 'list':
             if thumbnail_url != '':
                 r = '  <img src="' + thumbnail_url + '" alt="' + title + '" class="thumbnail"/>'
             else:
                 r = ''
         if ptype == 'atom':
             s = re.sub('\[http://'+urls[idx]+']', cgi.escape(r), s)
         else:
             s = re.sub('\[http://'+urls[idx]+']', r, s)
     return s
                                 
def slugify(s):
  s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore')
  return re.sub('[^a-zA-Z0-9]+', '-', s).strip('-').lower()


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


def get_template_vals_defaults(template_vals=None):
  if template_vals is None:
    template_vals = {}
  template_vals.update({
      'config': config,
      'devel': os.environ['SERVER_SOFTWARE'].startswith('Devel'),
  })
  return template_vals


def render_template(template_name, template_vals=None, theme=None):
  template_vals = get_template_vals_defaults(template_vals)
  template_vals.update({'template_name': template_name})
  old_settings = _swap_settings({'TEMPLATE_DIRS': TEMPLATE_DIRS})
  try:
    tpl = loader.get_template(template_name)
    rendered = tpl.render(template.Context(template_vals))
  finally:
    _swap_settings(old_settings)
  return rendered

def _get_all_paths():
  import static
  keys = []
  q = static.StaticContent.all(keys_only=True).filter('indexed', True)
  cur = q.fetch(1000)
  while len(cur) == 1000:
    keys.extend(cur)
    q = static.StaticContent.all(keys_only=True)
    q.filter('indexed', True)
    q.filter('__key__ >', cur[-1])
    cur = q.fetch(1000)
  keys.extend(cur)
  return [x.name() for x in keys]


def _regenerate_sitemap():
  import static
  import gzip
  from StringIO import StringIO
  paths = _get_all_paths()
  rendered = render_template('sitemap.xml', {'paths': paths})
  static.set('/sitemap.xml', rendered, 'application/xml', False)
  s = StringIO()
  gzip.GzipFile(fileobj=s,mode='wb').write(rendered)
  s.seek(0)
  renderedgz = s.read()
  static.set('/sitemap.xml.gz',renderedgz, 'application/x-gzip', False)
  if config.google_sitemap_ping:
      ping_googlesitemap()     

def ping_googlesitemap():
  import urllib
  from google.appengine.api import urlfetch
  google_url = 'http://www.google.com/webmasters/tools/ping?sitemap=http://' + config.host + '/sitemap.xml.gz'
  response = urlfetch.fetch(google_url, '', urlfetch.GET)
  if response.status_code / 100 != 2:
    raise Warning("Google Sitemap ping failed", response.status_code, response.content)