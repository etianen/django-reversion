"""
Transactional version control for Django models.

Project sponsored by Etianen.com

<http://www.etianen.com/>
"""


from django.db.models.signals import post_save, pre_delete

from reversion.receivers import save_version, save_deleted_version


post_save.connect(save_version)
pre_delete.connect(save_deleted_version)