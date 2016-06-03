Register your models with a subclass of :ref:`VersionAdmin`.

.. code:: python

    from django.contrib import admin
    from reversion.admin import VersionAdmin

    @admin.register(YourModel)
    class YourModelAdmin(VersionAdmin):

        pass

.. include:: /_include/post-register.rst
