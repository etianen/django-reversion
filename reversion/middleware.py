import sys
from reversion.revisions import revision_context_manager
from reversion.views import _request_creates_revision, _set_user_from_request, create_revision


class RevisionMiddleware(object):

    """Wraps the entire request in a revision."""

    def __init__(self, get_response=None):
        super(RevisionMiddleware, self).__init__()
        # Support Django 1.10 middleware.
        if get_response is not None:
            self.__call__ = create_revision()(get_response)

    def process_request(self, request):
        if _request_creates_revision(request):
            context = revision_context_manager.create_revision()
            context.__enter__()
            _set_user_from_request(request, revision_context_manager)
            if not hasattr(request, "_revision_middleware"):
                setattr(request, "_revision_middleware", {})
            request._revision_middleware[self] = context

    def _close_revision(self, request):
        if self in getattr(request, "_revision_middleware", {}):
            request._revision_middleware.pop(self).__exit__(*sys.exc_info())

    def process_response(self, request, response):
        self._close_revision(request)
        return response

    def process_exception(self, request, exception):
        self._close_revision(request)
