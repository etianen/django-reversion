"""
Transactional version control for Django models.

Project sponsored by Etianen.com

<http://www.etianen.com/>
"""


from django.db.models.signals import post_save

from reversion.receivers import save_version


post_save.connect(save_version)