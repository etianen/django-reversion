"""Middleware used by Reversion."""


from django.middleware.transaction import TransactionMiddleware

from reversion import revision


class RevisionMiddleware(TransactionMiddleware):
    
    """Wraps the entire request in a Revision."""
    
    def process_request(self, request):
        """Starts a new revision."""
        super(RevisionMiddleware, self).process_request(request)
        revision.start()
        
    def process_response(self, request, response):
        """Closes the revision."""
        try:
            revision.commit()
            return super(RevisionMiddleware, self).process_response(request, response)
        finally:
            revision.end()
        
    def process_exception(self, request, exception):
        """Closes the revision."""
        try:
            revision.rollback()
            return super(RevisionMiddleware, self).process_exception(request, exception)
        finally:
            revision.end()
