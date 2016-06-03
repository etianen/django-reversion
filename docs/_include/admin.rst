Register your models with a subclass of ``reversion.VersionAdmin``.

.. code:: python

    from django.contrib import admin
    from reversion.admin import VersionAdmin

    @admin.register(YourModel)
    class YourModelAdmin(VersionAdmin):

        pass

.. include:: _include/register.rst
