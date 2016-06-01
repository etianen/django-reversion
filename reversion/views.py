from functools import wraps
from reversion.revisions import revision_context_manager


def request_creates_revision(request):
    """Introspects the request, and returns True if the request should create a new revision."""
    return request.method not in ("OPTIONS", "GET", "HEAD")


def create_revision(revision_context_manager=revision_context_manager):
    """
    View decorator that wraps the request in a revision.

    The revision will have it's user set from the request automatically.
    """
    def decorator(func):
        @wraps(func)
        def do_revision_view(request, *args, **kwargs):
            if request_creates_revision(request):
                with revision_context_manager.create_revision():
                    revision_context_manager.set_user(request.user)
                    return func(request, *args, **kwargs)
                return func(request, *args, **kwargs)
        return do_revision_view
    return decorator


class RevisionMixin(object):

    """
    A class-based view mixin that wraps the request in a revision.

    The revision will have it's user set from the request automatically.
    """

    revision_context_manager = revision_context_manager

    def __init__(self, *args, **kwargs):
        super(RevisionMixin, self).__init__(*args, **kwargs)
        self.dispatch = create_revision(self.revision_context_manager)(self.dispatch)
