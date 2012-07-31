"""
Transactional version control for Django models.

Developed by Dave Hall.

<http://www.etianen.com/>
"""

import django, warnings

from reversion.revisions import default_revision_manager, revision_context_manager, VersionAdapter
from reversion.admin import VersionAdmin
from reversion.models import pre_revision_commit, post_revision_commit
from reversion.version import __version__ 


VERSION = __version__ 

SUPPORTED_DJANGO_VERSIONS = (
    (1, 4, 0),
    (1, 4, 1),
)

def check_django_version():
    """Checks the version of django being used, and issues a warning if incorrect."""
    if django.VERSION[:3] not in SUPPORTED_DJANGO_VERSIONS:
        format_version = lambda v: u".".join(unicode(n) for n in v)
        warnings.warn(
            (
                u"django-reversion %(reversion_version)s is intended for use with django %(supported_django_version)s. "
                u"You are running django %(django_version)s, so some features, such as admin integration, may not work. "
                u"Please see https://github.com/etianen/django-reversion/wiki/Compatible-Django-Versions"
            ) % {
                "reversion_version": format_version(VERSION),
                "supported_django_version": ' or '.join(format_version(v) for v in SUPPORTED_DJANGO_VERSIONS),
                "django_version": format_version(django.VERSION[:3]),
            }
        )
        
check_django_version()


# Legacy revision reference.
revision = default_revision_manager  # TODO: Deprecate eventually.


# Easy registration methods.
register = default_revision_manager.register
is_registered = default_revision_manager.is_registered
unregister = default_revision_manager.unregister
get_adapter = default_revision_manager.get_adapter
get_registered_models = default_revision_manager.get_registered_models


# Context management.
create_revision = revision_context_manager.create_revision

    
# Revision meta data.
get_db = revision_context_manager.get_db
set_db = revision_context_manager.set_db
get_user = revision_context_manager.get_user
set_user = revision_context_manager.set_user
get_comment = revision_context_manager.get_comment
set_comment = revision_context_manager.set_comment
add_meta = revision_context_manager.add_meta
get_ignore_duplicates = revision_context_manager.get_ignore_duplicates
set_ignore_duplicates = revision_context_manager.set_ignore_duplicates


# Low level API.
get_for_object_reference = default_revision_manager.get_for_object_reference
get_for_object = default_revision_manager.get_for_object
get_unique_for_object = default_revision_manager.get_unique_for_object
get_for_date = default_revision_manager.get_for_date
get_deleted = default_revision_manager.get_deleted
