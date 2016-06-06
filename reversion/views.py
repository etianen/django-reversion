from functools import wraps
from reversion.revisions import revision_context_manager


def _request_creates_revision(request):
    return request.method not in ("OPTIONS", "GET", "HEAD")


def _set_user_from_request(request, revision_context_manager):
    if hasattr(request, "user") and request.user.is_authenticated():
        revision_context_manager.set_user(request.user)


def create_revision(revision_context_manager=revision_context_manager, manage_manually=False, db=None):
    """
    View decorator that wraps the request in a revision.

    The revision will have it's user set from the request automatically.
    """
    def decorator(func):
        @wraps(func)
        def do_revision_view(request, *args, **kwargs):
            if _request_creates_revision(request):
                with revision_context_manager.create_revision(manage_manually=manage_manually, db=None):
                    _set_user_from_request(request, revision_context_manager)
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

    revision_manage_manually = False

    revision_db = False

    def __init__(self, *args, **kwargs):
        super(RevisionMixin, self).__init__(*args, **kwargs)
        self.dispatch = create_revision(
            revision_context_manager=self.revision_context_manager,
            manage_manually=self.revision_manage_manually,
            db=self.revision_db,
        )(self.dispatch)
