from functools import wraps

from reversion.compat import is_authenticated
from reversion.revisions import create_revision as create_revision_base, set_user, get_user, set_comment


class _RollBackRevisionView(Exception):

    def __init__(self, response):
        self.response = response


def _request_creates_revision(request):
    return request.method not in ("OPTIONS", "GET", "HEAD")


def _set_user_from_request(request):
    if getattr(request, "user", None) and is_authenticated(request.user) and get_user() is None:
        set_user(request.user)


def create_revision(manage_manually=False, using=None, atomic=True, comment_func=None):
    """
    View decorator that wraps the request in a revision.

    The revision will have it's user set from the request automatically.
    """
    def decorator(func):
        @wraps(func)
        def do_revision_view(request, *args, **kwargs):
            if _request_creates_revision(request):
                try:
                    with create_revision_base(manage_manually=manage_manually, using=using, atomic=atomic):
                        response = func(request, *args, **kwargs)
                        # Check for an error response.
                        if response.status_code >= 400:
                            raise _RollBackRevisionView(response)
                        # Otherwise, we're good.
                        _set_user_from_request(request)
                        if comment_func:
                            set_comment(comment_func(request))
                        return response
                except _RollBackRevisionView as ex:
                    return ex.response
            return func(request, *args, **kwargs)
        return do_revision_view
    return decorator


class RevisionMixin(object):

    """
    A class-based view mixin that wraps the request in a revision.

    The revision will have it's user set from the request automatically.
    """

    revision_manage_manually = False

    revision_using = None

    revision_atomic = True

    revision_comment_method = 'create_revision_comment'

    def __init__(self, *args, **kwargs):
        super(RevisionMixin, self).__init__(*args, **kwargs)
        comment_method = getattr(self, self.revision_comment_method, None)
        self.dispatch = create_revision(
            manage_manually=self.revision_manage_manually,
            using=self.revision_using,
            atomic=self.revision_atomic,
            comment_func=comment_method
        )(self.dispatch)
