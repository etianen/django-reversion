"""Errors raised by django-reversion."""
    
    
class RevertError(Exception):
    
    """Exception thrown when something goes wrong with reverting a model."""