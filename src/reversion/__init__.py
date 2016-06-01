"""
Transactional version control for Django models.

Developed by Dave Hall.

<http://www.etianen.com/>
"""

from reversion.version import __version__  # noqa
from reversion.revisions import (  # noqa
    VersionAdapter,
    RevisionManager,
    # Singletons.
    revision_context_manager,
    default_revision_manager,
    # Easy registration methods.
    register,
    is_registered,
    unregister,
    get_adapter,
    get_registered_models,
    # Manual revision saving.
    save_revision,
    # Context management.
    create_revision,
    # Revision meta data.
    get_user,
    set_user,
    get_comment,
    set_comment,
    add_meta,
    get_ignore_duplicates,
    set_ignore_duplicates,
    # Low level API.
    get_for_object_reference,
    get_for_object,
    get_unique_for_object,
    get_for_date,
    get_deleted,
)
