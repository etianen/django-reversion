"""
An extension to the Django web framework that provides version control for model instances.

Developed by Dave Hall.

<http://www.etianen.com/>
"""

try:
    import django  # noqa
except ImportError:  # pragma: no cover
    # The top-level API requires Django, which might not be present if setup.py
    # is importing reversion to get __version__.
    pass
else:
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

__version__ = VERSION = (1, 10, 3)
