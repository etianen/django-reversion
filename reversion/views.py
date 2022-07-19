from functools import wraps
import reversion

from reversion.revisions import create_revision as create_revision_base, set_user, get_user
from reversion.admin import _RollBackRevisionView


def _request_creates_revision(request):
    return request.method not in ("OPTIONS", "GET", "HEAD")


def _set_user_from_request(request):
    if getattr(request, "user", None) and request.user.is_authenticated and get_user() is None:
        set_user(request.user)


def create_revision(
    manage_manually=False,
    using=None,
    atomic=True,
    request_creates_revision=None,
):
    request_creates_revision = (
        request_creates_revision or _request_creates_revision
    )

    def decorator(func):
        @wraps(func)
        def do_revision_view(request, *args, **kwargs):
            if request_creates_revision(request):
                try:
                    with create_revision_base(
                        manage_manually=manage_manually,
                        using=using,
                        atomic=atomic,
                    ):
                        response = func(request, *args, **kwargs)
                        # Check for an error response.
                        if response.status_code >= 400:
                            raise _RollBackRevisionView(response)
                        # Otherwise, we're good.
                        _set_user_from_request(request)

                        # Additional calls
                        reversion.set_comment(request.path)

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dispatch = create_revision(
            manage_manually=self.revision_manage_manually,
            using=self.revision_using,
            atomic=self.revision_atomic,
            request_creates_revision=self.revision_request_creates_revision
        )(self.dispatch)

    def revision_request_creates_revision(self, request):
        return _request_creates_revision(request)
