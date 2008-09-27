"""File storage implementation for version controlled files."""


from django.core.files.storage import get_storage_class

from reversion.settings import VERSION_FILE_STORAGE


class VersionFileStorage(object):
    
    """
    Proxy storage mechanism that stores version controlled files by piggbacking
    on another storage mechanism.
    """
    
    def __init__(self, storage_implementation=None):
        """
        Initializes the VersionFileStorage.
        
        storage_implementation should be an instance of a Storage class.  If
        left blank, the value of settings.VERSION_FILE_STORAGE will be used.
        """
        self._storage_implementation = storage_implementation or get_storage_class(VERSION_FILE_STORAGE)()
        
    def __getattr__(self, name):
        """Proxies storage mechanism to the wrapped implementation."""
        return getattr(self._storage_implementation, name)
    
    def delete(self, name):
        """File deletions are blocked for this storage class."""
        pass