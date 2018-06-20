.. _views:

Views
=====

Shortcuts when using django-reversion in views.


Decorators
----------

``reversion.views.create_revision(manage_manually=False, using=None, atomic=True, request_creates_revision=None)``

    Decorates a view to wrap every request in a revision block.

    The request user will also be added to the revision metadata. You can set the revision comment by calling :ref:`reversion.set_comment() <set_comment>` within your view.

    .. include:: /_include/create-revision-args.rst

    ``request_creates_revision``

        Hook used to decide whether a request should be wrapped in a revision block. If ``None``, it will default to omitting ``GET``, ``HEAD`` and ``OPTIONS`` requests.


reversion.views.RevisionMixin
-----------------------------

Mixin a class-based view to wrap every request in a revision block.

The request user will also be added to the revision metadata. You can set the revision comment by calling :ref:`reversion.set_comment() <set_comment>` within your view.

.. code:: python

    from django.contrib.auth.views import FormView
    from reversion.views import RevisionMixin

    class RevisionFormView(RevisionMixin, FormView):

        pass


``RevisionMixin.revision_manage_manually = False``

    .. include:: /_include/create-revision-manage-manually.rst


``RevisionMixin.revision_using = None``

    .. include:: /_include/create-revision-using.rst

``RevisionMixin.revision_request_creates_revision(request)``

    By default, any request that isn't ``GET``, ``HEAD`` or ``OPTIONS`` will be wrapped in a revision block. Override this method if you need to apply a custom rule.
