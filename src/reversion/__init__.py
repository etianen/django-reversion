"""
Transactional version control for Django models.

Developed by Dave Hall.

<http://www.etianen.com/>
"""

from reversion.revisions import revision, revision_context_manager
from reversion.admin import VersionAdmin


# Easy registration methods.
register = revision.register
is_registered = revision.is_registered
unregister = revision.unregister
get_adapter = revision.get_adapter


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