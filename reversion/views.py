from functools import wraps
from reversion.revisions import create_revision as create_revision_base, set_user


def _request_creates_revision(request):
    return request.method not in ("OPTIONS", "GET", "HEAD")


def _set_user_from_request(request):
    if hasattr(request, "user") and request.user.is_authenticated():
        set_user(request.user)


def create_revision(manage_manually=False, using=None):
    """
    View decorator that wraps the request in a revision.

    The revision will have it's user set from the request automatically.
    """
    def decorator(func):
        @wraps(func)
        def do_revision_view(request, *args, **kwargs):
            if _request_creates_revision(request):
                with create_revision_base(manage_manually=manage_manually, using=None):
                    _set_user_from_request(request)
                    return func(request, *args, **kwargs)
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

    def __init__(self, *args, **kwargs):
        super(RevisionMixin, self).__init__(*args, **kwargs)
        self.dispatch = create_revision(
            manage_manually=self.revision_manage_manually,
            using=self.revision_using,
        )(self.dispatch)
