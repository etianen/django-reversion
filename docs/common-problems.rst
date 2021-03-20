.. _common-problems:

Common problems
===============

Incompatible version data
-------------------------

Django-reversion stores the versions of a model as JSON. If a model changes, the migrations are not applied to the stored JSON data. Therefore it can happen that an old version can no longer be restored. In this case the following error occurs:

.. code:: python

    reversion.errors.RevertError: Could not load <Foo: bar> - incompatible version data.


RegistrationError: class 'myapp.MyModel' has already been registered with Reversion
-----------------------------------------------------------------------------------

This is caused by your ``models.py`` file being imported twice, resulting in ``reversion.register()`` being called twice for the same model.

This problem is almost certainly due to relative import statements in your codebase. Try converting all your relative imports into absolute imports.
