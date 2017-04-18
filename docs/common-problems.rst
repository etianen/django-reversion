.. _common-problems:

Common problems
===============


RegistrationError: class 'myapp.MyModel' has already been registered with Reversion
-----------------------------------------------------------------------------------

This is caused by your ``models.py`` file being imported twice, resulting in ``reversion.register()`` being called twice for the same model.

This problem is almost certainly due to relative import statements in your codebase. Try converting all your relative imports into absolute imports.
