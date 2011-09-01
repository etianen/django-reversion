"""
Transactional version control for Django models.

Developed by Dave Hall.

<http://www.etianen.com/>
"""

from reversion.revisions import revision, revision_context_manager, VersionAdapter
from reversion.admin import VersionAdmin


# Easy registration methods.
register = revision.register
is_registered = revision.is_registered
unregister = revision.unregister
get_adapter = revision.get_adapter
get_registered_models = revision.get_registered_models


# Context management.
create_revision = revision_context_manager.create_revision
context = revision_context_manager.context

    
# Revision meta data.
get_user = revision_context_manager.get_user
set_user = revision_context_manager.set_user
get_comment = revision_context_manager.get_comment
set_comment = revision_context_manager.set_comment
add_meta = revision_context_manager.add_meta
get_ignore_duplicates = revision_context_manager.get_ignore_duplicates
set_ignore_duplicates = revision_context_manager.set_ignore_duplicates


# Low level API.
get_for_object_reference = revision.get_for_object_reference
get_for_object = revision.get_for_object
get_unique_for_object = revision.get_unique_for_object
get_for_date = revision.get_for_date
get_deleted = revision.get_deleted