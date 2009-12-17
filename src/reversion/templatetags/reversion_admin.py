"""Template tags used by the Reversion admin integration."""


from django import template
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe


register = template.Library()


@register.filter
def fix_jsi18n(extrahead):
    """
    Hack to rewrite out the jsi18n script tag from an inherited admin template.
    
    This is required in order to prevent it's relative path from generating
    server errors.
    
    Please see this issue for more information:
    
        * http://code.google.com/p/django-reversion/issues/detail?id=50
    """
    return mark_safe(unicode(extrahead).replace(u"../../../jsi18n/", reverse("admin:jsi18n")))

