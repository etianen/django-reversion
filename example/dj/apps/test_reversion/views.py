from django.utils.decorators import decorator_from_middleware as django_decorator_from_middleware
from django.http import HttpResponse
from django.conf import settings

from reversion.middleware import RevisionMiddleware

from test_reversion.models import ReversionTestModel1, ReversionTestModel2


# RevisionMiddleware is tested by applying it as a decorator to various view
# functions. Django's decorator_from_middleware() utility function does the
# trick of converting a middleware class to a decorator. However, in projects
# that include the middleware in the MIDDLEWARE_CLASSES setting, the wrapped
# view function is processed twice by the middleware. When RevisionMiddleware
# processes a function twice, an ImproperlyConfigured exception is raised.
# Thus, using Django's definition of decorator_from_middleware() can prevent
# reversion integration tests from passing in projects that include
# RevisionMiddleware in MIDDLEWARE_CLASSES.
#
# To avoid this problem, we redefine decorator_from_middleware() to return a
# decorator that does not reapply the middleware if it is in
# MIDDLEWARE_CLASSES.  @decorator_from_middleware(RevisionMiddleware) is then
# used to wrap almost all RevisionMiddleware test views. The only exception is
# double_middleware_revision_view(), which needs to be doubly processed by
# RevisionMiddleware.  This view is wrapped twice with
# @django_decorator_from_middleware(RevisionMiddleware), where
# django_decorator_from_middleware() is imported as Django's definition of
# decorator_from_middleware().

revision_middleware_django_decorator = django_decorator_from_middleware(RevisionMiddleware)

def decorator_from_middleware(middleware_class):
    """
    This is a wrapper around django.utils.decorators.decorator_from_middleware
    (imported as django_decorator_from_middleware). If the middleware class is
    not loaded via MIDDLEWARE_CLASSES in the project settings, then the
    middleware decorator is returned. However, if the middleware is already
    loaded, then an identity decorator is returned instead, so that the
    middleware does not process the view function twice.
    """
    middleware_path = "%s.%s" % (middleware_class.__module__,
                                 middleware_class.__name__)
    if middleware_path in settings.MIDDLEWARE_CLASSES:  # pragma: no cover
        return lambda view_func: view_func
    return django_decorator_from_middleware(middleware_class)

revision_middleware_decorator = decorator_from_middleware(RevisionMiddleware)

# A dumb view that saves a revision.
@revision_middleware_decorator
def save_revision_view(request):
    ReversionTestModel1.objects.create(
        name = "model1 instance3 version1",
    )
    ReversionTestModel1.objects.create(
        name = "model1 instance4 version1",
    )
    ReversionTestModel2.objects.create(
        name = "model2 instance3 version1",
    )
    ReversionTestModel2.objects.create(
        name = "model2 instance4 version1",
    )
    return HttpResponse("OK")


# A dumb view that borks a revision.
@revision_middleware_decorator
def error_revision_view(request):
    ReversionTestModel1.objects.create(
        name = "model1 instance3 version1",
    )
    ReversionTestModel1.objects.create(
        name = "model1 instance4 version1",
    )
    ReversionTestModel2.objects.create(
        name = "model2 instance3 version1",
    )
    ReversionTestModel2.objects.create(
        name = "model2 instance4 version1",
    )
    raise Exception("Foo")


# A dumb view that has two revision middlewares.
@revision_middleware_django_decorator
@revision_middleware_django_decorator
def double_middleware_revision_view(request):
    assert False
