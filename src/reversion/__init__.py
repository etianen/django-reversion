"""
Transactional version control for Django models.

Developed by Dave Hall.

<http://www.etianen.com/>
"""

from reversion.revisions import revision
from reversion.admin import VersionAdmin


# Easy registration methods.
register = revision.register
is_registered = revision.is_registered
unregister = revision.unregister
get_adapter = revision.get_adapter


# Context management.
create_revision = revision.create_on_success

def context():
    """Defines a new revision management context."""
    return revision

    
# Revision meta data.
get_user = revision.get_user
set_user = revision.set_user
get_comment = revision.get_comment
set_comment = revision.set_comment
add_meta = revision.add_meta
get_ignore_duplicates = revision.get_ignore_duplicates
set_ignore_duplicates = revision.set_ignore_duplicates