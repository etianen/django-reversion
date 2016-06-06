``model``
    A Django model to store the custom metadata. The model must have a ``ForeignKey`` or ``OneToOneField`` to :ref:`Revision`.

``**values``
    Values to be stored on ``model`` when it is saved.
