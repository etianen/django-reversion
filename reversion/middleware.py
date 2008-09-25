"""Middleware used by Reversion."""


from django.middleware.transaction import TransactionMiddleware

from reversion import revision


class RevisionMiddleware(TransactionMiddleware):
    
    """
    Wraps the entire request in a Revision.
    
    The request will also be placed under transaction management.
    """
    
    def process_request(self, request):
        """Starts a new revision."""
        super(RevisionMiddleware, self).process_request(request)
        if request.user.is_authenticated():
            user = request.user
        else:
            user = None
        revision.start("%s request to %s" % (request.method, request.get_full_path()), user)
        
    def process_response(self, request, response):
        """Closes the revision."""
        try:
            revision.end()
        finally:
            return super(RevisionMiddleware, self).process_response(request, response)
        
    def process_exception(self, request, exception):
        """Closes the revision."""
        try:
            revision.end()
        finally:
            return super(RevisionMiddleware, self).process_exception(request, exception)