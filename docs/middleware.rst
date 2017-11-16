.. _middleware:

Middleware
==========

Shortcuts when using django-reversion in views.


reversion.middleware.RevisionMiddleware
---------------------------------------

Wrap the every request that isn't ``GET``, ``HEAD`` or ``OPTIONS`` in a revision block.

The request user will also be added to the revision metadata.

To enable ``RevisionMiddleware``, add ``'reversion.middleware.RevisionMiddleware'`` to your ``MIDDLEWARE_CLASSES`` setting. For Django >= 1.10, add it to your ``MIDDLEWARE`` setting.

To enable including or excluding models while using the ``'reversion.middleware.RevisionMiddleware'`` you need to add to your settings ``DJANGO_REVISION_CUSTOM_MODELS = True`` and add either ``DJANGO_REVISION_EXCLUDED_MODELS = ['MODELNAME']`` or ``DJANGO_REVISION_EXCLUDED_MODELS = ['DJANGO_REVISION_ALLOWED_MODELS']``

.. Warning::
This will wrap every request that isn't ``GET``, ``HEAD`` or ``OPTIONS`` in a database transaction. For best performance, consider marking individual views instead.


``RevisionMiddleware.manage_manually = False``

    .. include:: /_include/create-revision-manage-manually.rst


``RevisionMiddleware.using = None``

    .. include:: /_include/create-revision-using.rst


``RevisionMiddleware.atomic = True``

    .. include:: /_include/create-revision-atomic.rst
