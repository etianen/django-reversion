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

# Context management.
create_on_success = revision.create_on_success