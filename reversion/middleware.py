"""Middleware used by Reversion."""


from reversion import revision


class RevisionMiddleware(object):
    
    """Wraps the entire request in a Revision."""
    
    def process_request(self, request):
        """Starts a new revision."""
        revision.start()
        
    def process_response(self, request, response):
        """Closes the revision."""
        revision.end()
        
    def process_exception(self, request, exception):
        """Closes the revision."""
        revision.end()