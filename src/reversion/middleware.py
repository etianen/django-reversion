"""Middleware used by Reversion."""


import sys

import reversion
from reversion.revisions import RevisionManagementError


class RevisionMiddleware(object):
    
    """Wraps the entire request in a revision."""
    
    def process_request(self, request):
        """Starts a new revision."""
        reversion.revision.start()
        if request.user.is_authenticated():
            reversion.revision.user = request.user
        
    def process_response(self, request, response):
        """Closes the revision."""
        if reversion.revision.is_active():
            reversion.revision.end()
            if reversion.revision.is_active():
                raise RevisionManagementError, "Request terminated with pending revision."
        return response
        
    def process_exception(self, request, exception):
        """Closes the revision."""
        reversion.revision.invalidate()
        
        