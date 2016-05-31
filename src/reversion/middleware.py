from __future__ import unicode_literals
import warnings
from reversion.revisions import revision_context_manager
from reversion.views import request_creates_revision, create_revision


class RevisionMiddleware(object):

    """Wraps the entire request in a revision."""

    def __init__(self, get_response=None):
        super(RevisionMiddleware, self).__init__()
        if get_response is None:
            # Warn about using old-style middleware.
            warnings.warn((
                "Using RevisionMiddleware in MIDDLEWARE_CLASSES breaks transactional isolation. "
                "For Django >= 1.10, upgrade to using MIDDLEWARE instead. "
                "For Django <= 1.9, use reversion.views.RevisionMixin instead. "
                "Support for Django <= 1.9 MIDDLEWARE_CLASSES will be removed in django-reversion 1.11.0."
            ), DeprecationWarning)
        else:
            # Support Django 1.10 middleware.
            self.__call__ = create_revision()(get_response)

    def process_request(self, request):
        if request_creates_revision(request):
            revision_context_manager.start()
            revision_context_manager.set_user(request.user)
            if not hasattr(request, "_revision_middleware"):
                setattr(request, "_revision_middleware", set())
            request._revision_middleware.add(self)

    def _close_revision(self, request, invalidate):
        if self in getattr(request, "_revision_middleware", ()):
            if invalidate:
                revision_context_manager.invalidate()
            revision_context_manager.end()
            request._revision_middleware.remove(self)

    def process_response(self, request, response):
        self._close_revision(request, invalidate=False)
        return response

    def process_exception(self, request, exception):
        self._close_revision(request, invalidate=True)
