"""Default settings for Reversion."""


from django.db import settings


# A tuple of models that should be placed under version control.  Each model
# should be in the form app_label.ModelName.
try:
    VERSION_CONTROLLED_MODELS = settings.VERSION_CONTROLLED_MODELS
except AttributeError:
    VERSION_CONTROLLED_MODELS = ()
    

# The file storage implementation used by the version file storage mechanism.
# This will be used to store version controlled files.
try:
    VERSION_FILE_STORAGE = settings.VERSION_FILE_STORAGE
except AttributeError:
    VERSION_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"