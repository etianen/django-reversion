"""Signal receivers used by Reversion."""


from reversion.models import Version
from reversion.settings import VERSION_CONTROLLED_MODELS


def save_version(sender, instance, **kwargs):
    """Signal handler to save a version whenever a model is saved."""
    app_label = sender._meta.app_label
    model_name = sender.__name__
    model_identifier = ".".join((app_label, model_name))
    if model_identifier in VERSION_CONTROLLED_MODELS:
        Version.objects.save_version(instance)