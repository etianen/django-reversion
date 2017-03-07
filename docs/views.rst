.. _views:

Views
=====

Shortcuts when using django-reversion in views.


Decorators
----------

``reversion.views.create_revision(manage_manually=False, using=None, atomic=True)``

    Decorates a view to wrap every request that isn't ``GET``, ``HEAD`` or ``OPTIONS`` in a revision block.

    The request user will also be added to the revision metadata. You can set the revision comment by calling :ref:`reversion.set_comment() <set_comment>` within your view.

    .. include:: /_include/create-revision-args.rst


reversion.views.RevisionMixin
-----------------------------

Mixin a class-based view to wrap every request that isn't ``GET``, ``HEAD`` or ``OPTIONS`` in a revision block.

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
