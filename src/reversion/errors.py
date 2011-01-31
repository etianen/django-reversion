"""Errors raised by django-reversion."""


class RevisionManagementError(Exception):
    
    """
    Exception that is thrown when something goes wrong with revision managment.
    """
    

class RegistrationError(Exception):
    
    """Exception thrown when registration with Reversion goes wrong."""
    
    
class RevertError(Exception):
    
    """Exception thrown when something goes wrong with reverting a model."""