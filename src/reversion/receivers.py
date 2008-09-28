"""Signal receivers used by Reversion."""


from reversion import revision


def save_version(sender, instance, **kwargs):
    """Signal handler to save a version whenever a model is saved."""
    revision.add(instance)
        
        
def save_deleted_version(sender, instance, **kwargs):
    """Signal handler to save a version whenever a model is saved."""
    revision.add(instance, commit=True)