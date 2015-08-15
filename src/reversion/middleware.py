"""Middleware used by Reversion."""

from __future__ import unicode_literals

from django.core.exceptions import ImproperlyConfigured

from reversion.revisions import revision_context_manager


REVISION_MIDDLEWARE_FLAG = "reversion.revision_middleware_active"


class RevisionMiddleware(object):  # pragma: no cover

    """Wraps the entire request in a revision."""

    def process_request(self, request):
        """Starts a new revision."""
        if request.META.get(REVISION_MIDDLEWARE_FLAG, False):
            raise ImproperlyConfigured("RevisionMiddleware can only be included in MIDDLEWARE_CLASSES once.")
        request.META[REVISION_MIDDLEWARE_FLAG] = True
        revision_context_manager.start()

    def _close_revision(self, request):
        """Closes the revision."""
        if request.META.get(REVISION_MIDDLEWARE_FLAG, False):
            del request.META[REVISION_MIDDLEWARE_FLAG]
            revision_context_manager.end()

    def process_response(self, request, response):
        """Closes the revision."""
        # look to see if the session has been accessed before looking for user to stop Vary: Cookie
        if hasattr(request, 'session') and request.session.accessed \
                and hasattr(request, "user") and request.user is not None and request.user.is_authenticated() \
                and revision_context_manager.is_active():
            revision_context_manager.set_user(request.user)
        self._close_revision(request)
        return response

    def process_exception(self, request, exception):
        """Closes the revision."""
        revision_context_manager.invalidate()
        self._close_revision(request)
