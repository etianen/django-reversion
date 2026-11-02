"""
An extension to the Django web framework that provides version control for model instances.

Developed by Dave Hall.

<http://www.etianen.com/>
"""

from reversion.errors import (  # noqa
    RevertError,
    RevisionManagementError,
    RegistrationError,
)
from reversion.revisions import (  # noqa
    is_active,
    is_manage_manually,
    get_user,
    set_user,
    get_comment,
    set_comment,
    get_date_created,
    set_date_created,
    add_meta,
    add_to_revision,
    create_revision,
    register,
    is_registered,
    unregister,
    get_registered_models,
)

__version__ = VERSION = (6, 5, 0)
