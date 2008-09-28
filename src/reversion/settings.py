"""Default settings for Reversion."""


from django.db import settings


# The file storage implementation used by the version file storage mechanism.
# This will be used to store version controlled files.
try:
    VERSION_FILE_STORAGE = settings.VERSION_FILE_STORAGE
except AttributeError:
    VERSION_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"