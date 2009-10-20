# Name of the blog
blog_name = 'Bloggart demo'

# Your name (used for copyright info)
author_name = 'the author'

# (Optional) slogan
slogan = 'Blogging on App Engine'

# The hostname this site will primarially serve off (used for Atom feeds)
host = 'bloggart-demo.appspot.com'

# Selects the theme to use. Theme names correspond to directories under
# the 'themes' directory, containing templates and static content.
theme = 'default'

# Defines the URL organization to use for blog postings. Valid substitutions:
#   slug - the identifier for the post, derived from the title
#   year - the year the post was published in
#   month - the month the post was published in
#   day - the day the post was published in
post_path_format = '/%(year)d/%(month)02d/%(slug)s'

# A nested list of sidebar menus, for convenience. If this isn't versatile
# enough, you can edit themes/default/base.html instead.
sidebars = [
  ('Blogroll', [
    ('Nick Johnson', 'http://blog.notdot.net/'),
    ('Bill Katz', 'http://www.billkatz.com/'),
    ('Coding Horror', 'http://www.codinghorror.com/blog/'),
    ('Craphound', 'http://craphound.com/'),
    ('Neopythonic', 'http://www.neopythonic.blogspot.com/'),
    ('Schneier on Security', 'http://www.schneier.com/blog/'),
  ]),
]

# Number of entries per page in indexes.
posts_per_page = 10

# The mime type to serve HTML files as.
html_mime_type = "text/html; charset=utf-8"

# To use disqus for comments, set this to the 'short name' of the disqus forum
# created for the purpose.
disqus_forum = None

# Length (in words) of summaries, by default
summary_length = 200
