"""Default settings for Reversion."""


from django.db import settings


# A tuple of models that should be placed under version control.  Each model
# should be in the form app_label.ModelName.
try:
    VERSION_CONTROLLED_MODELS = frozenset(settings.VERSION_CONTROLLED_MODELS)
except AttributeError:
    VERSION_CONTROLLED_MODELS = frozenset()