.. _signals:

Signals sent by django-reversion
================================

django-reversion provides a number of custom signals that can be used to tie-in additional functionality to the version creation mechanism.

**Important:** Don't connect to the pre_save or post_save signals of the Version or Revision models directly, use the signals outlined below instead. The pre_save and post_save signals are no longer sent by the Version or Revision models since django-reversion 1.7.

reversion.pre_revision_commit
-----------------------------

This signal is triggered just before a revision is saved to the database. It receives the following keyword arguments:

* **instances** - A list of the model instances in the revision.
* **revision** - The unsaved Revision model.
* **versions** - The unsaved Version models in the revision.


reversion.post_revision_commit
------------------------------

This signal is triggered just after a revision is saved to the database. It receives the following keyword arguments:

* **instances** - A list of the model instances in the revision.
* **revision** - The saved Revision model.
* **versions** - The saved Version models in the revision.


Connecting to signals
---------------------

The signals listed above are sent only once *per revision*, rather than once *per model in the revision*. In practice, this means that you should connect to the signals without specifying a `sender`, as below::

    def on_revision_commit(**kwargs):
        pass  # Your signal handler code here.
    reversion.post_revision_commit.connect(on_revision_commit)

To execute code only when a revision has been saved for a particular Model, you should inspect the contents of the `instances` parameter, as below::

    def on_revision_commit(instances, **kwargs):
        for instance in instances:
            if isinstance(instance, MyModel):
                pass  # Your signal handler code here.
    reversion.post_revision_commit.connect(on_revision_commit)
