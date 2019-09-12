.. _middleware:

Middleware
==========

Shortcuts when using django-reversion in views.


reversion.middleware.RevisionMiddleware
---------------------------------------

Wrap every request in a revision block.

The request user will also be added to the revision metadata.

To enable ``RevisionMiddleware``, add ``'reversion.middleware.RevisionMiddleware'`` to your ``MIDDLEWARE`` setting.

.. Warning::
    This will wrap every request that meets the specified criterion in a database transaction. For best performance, consider marking individual views instead.


``RevisionMiddleware.manage_manually = False``

    .. include:: /_include/create-revision-manage-manually.rst


``RevisionMiddleware.using = None``

    .. include:: /_include/create-revision-using.rst


``RevisionMiddleware.atomic = True``

    .. include:: /_include/create-revision-atomic.rst

``RevisionMiddleware.request_creates_revision(request)``

    By default, any request that isn't ``GET``, ``HEAD`` or ``OPTIONS`` will be wrapped in a revision block. Override this method if you need to apply a custom rule.

    For example:

    .. code:: python

          from reversion.middleware import RevisionMiddleware

          class BypassRevisionMiddleware(RevisionMiddleware):

              def request_creates_revision(self, request):
                  # Bypass the revision according to some header
                  silent = request.META.get("HTTP_X_NOREVISION", "false")
                  return super().request_creates_revision(request) and \
                      silent != "true"
