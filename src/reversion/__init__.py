"""
Transactional version control for Django models.

Project sponsored by Etianen.com

<http://www.etianen.com/>
"""


from django.db.models.signals import post_save, pre_delete

from reversion.receivers import save_version, save_deleted_version


def register(model_class):
    """Registers a model for version control."""
    post_save.connect(save_version, model_class)
    pre_delete.connect(save_deleted_version, model_class)
        
    
def unregister(model_class):
    """Removes a model from version control."""
    post_save.disconnect(save_version, model_class)
    pre_delete.disconnect(save_deleted_version, model_class)