from pathlib import Path
import zlib
import logging

from django.conf import settings

logger = logging.getLogger(__name__)
ENCODING = "utf-8"
FILE_ROOT = getattr(settings, "VERSION_FILE_ROOT", settings.MEDIA_ROOT)
DIRNAME = getattr(settings, "VERSION_DIRNAME", "versions")
version_root = Path(FILE_ROOT) / DIRNAME
version_root.mkdir(exist_ok=True)

ARCHIVE_ENABLED = getattr(settings, "VERSION_ARCHIVE_ENABLED", False)


def get_file_path(pk):
    return version_root / f"version-{pk}.txt"


def read(pk):
    if not ARCHIVE_ENABLED:
        return

    file = get_file_path(pk)
    if file.exists():
        compressed = file.read_bytes()
        content = zlib.decompress(compressed).decode(ENCODING)
        return content


def write(pk, content):
    if not ARCHIVE_ENABLED:
        return

    file = get_file_path(pk)
    compressed = zlib.compress(content.encode(ENCODING))
    file.write_bytes(compressed)
