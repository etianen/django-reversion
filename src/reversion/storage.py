"""File storage wrapper for version controlled file fields."""


class VersionFileStorageWrapper(object):
    
    """Wrapper for file storage implementations that blocks file deletions."""
    
    __slots__ = "wrapped_storage",
    
    def __init__(self, storage):
        """Initializes the VersionFileStorageWrapper."""
        self.wrapped_storage = storage
        
    def __getattr__(self, name):
        """Proxies storage mechanism to the wrapped implementation."""
        return getattr(self.wrapped_storage, name)
    
    def delete(self, name):
        """File deletions are blocked for this storage class."""
        pass

