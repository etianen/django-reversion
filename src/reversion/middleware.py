import sys
from reversion.revisions import revision_context_manager
from reversion.views import request_creates_revision, create_revision


class RevisionMiddleware(object):

    """Wraps the entire request in a revision."""

    def __init__(self, get_response=None):
        super(RevisionMiddleware, self).__init__()
        # Support Django 1.10 middleware.
        if get_response is not None:
            self.__call__ = create_revision()(get_response)

    def process_request(self, request):
        if request_creates_revision(request):
            revision_context_manager._start()
            revision_context_manager.set_user(request.user)
            if not hasattr(request, "_revision_middleware"):
                setattr(request, "_revision_middleware", set())
            request._revision_middleware.add(self)

    def _close_revision(self, request):
        if self in getattr(request, "_revision_middleware", ()):
            revision_context_manager._end(*sys.exc_info())
            request._revision_middleware.remove(self)

    def process_response(self, request, response):
        self._close_revision(request)
        return response

    def process_exception(self, request, exception):
        self._close_revision(request)
