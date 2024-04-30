from itertools import islice
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor

from django.utils import timezone
from django.conf import settings
from reversion.models import Revision, Version

KEEP_DAYS = getattr(settings, "VERSION_KEEP_DAYS", 30)
BATCH_SIZE = getattr(settings, "VERSION_BATCH_SIZE", 100)


def batched(iterable, n):
    if n < 1:
        raise ValueError("n must be at least one")
    it = iter(iterable)
    while batch := tuple(islice(it, n)):
        yield batch


def get_stale_revisions(keep_days=KEEP_DAYS):
    cutoff = timezone.now() - timedelta(days=keep_days)
    return Revision.objects.filter(date_created__lt=cutoff)


def get_stale_versions(keep_days=KEEP_DAYS, batch_size=BATCH_SIZE, get_batched=True):
    revisions = get_stale_revisions(keep_days)
    versions = (
        Version.objects.filter(revision_id__in=revisions)
        .exclude(is_archived=True)
        .iterator()
    )
    if get_batched:
        return batched(versions, batch_size)
    else:
        return versions


def get_archived(batch_size=BATCH_SIZE, get_batched=True):
    versions = Version.objects.filter(is_archived=True).iterator()
    if get_batched:
        return batched(versions, batch_size)
    else:
        return versions


def archive_versions(versions):
    for version in versions:
        version.archive()


def restore_versions(versions):
    for version in versions:
        version.restore()


def batch_archive_versions(keep_days=KEEP_DAYS, batch_size=BATCH_SIZE):
    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(
            archive_versions,
            get_stale_versions(keep_days=keep_days, batch_size=batch_size),
        )


def batch_restore_versions(batch_size=BATCH_SIZE):
    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(restore_versions, get_archived(batch_size=batch_size))
