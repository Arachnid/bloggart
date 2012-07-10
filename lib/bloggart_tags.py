from django.template import Library
register = Library()

@register.filter
def rfc3339(value):
    from django.utils.dateformat import DateFormat
    if not value:
        return u''
    try:
        df = DateFormat(value)
        offset = (lambda seconds: u"%+03d:%02d" % (seconds // 3600, (seconds // 60) % 60))(df.Z())
        return df.format("Y-m-d\TH:i:s") + offset
    except AttributeError:
        return ''
