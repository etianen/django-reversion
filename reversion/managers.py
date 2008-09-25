"""Managers used by Reversion."""


from django.db import models


class VersionManager(models.Manager):
    
    """Manager for Version models."""
    
    def save_version(self, model):
        """Saves a version of the given model."""
        return self.create(object_version=model)