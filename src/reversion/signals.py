from django.dispatch.dispatcher import Signal


# Signal sent just before a new Revision object is saved to the database.
pre_revision_commit = Signal(providing_args=["instances", "revision", "versions"])


# Signal sent just after a new Revision object is saved to the database.
post_revision_commit = Signal(providing_args=["instances", "revision", "versions"])


# Signal sent just
post_revision_context_end = Signal(providing_args=[
    "objects",
    "serialized_objects",
    "ignore_duplicates",
    "user",
    "comment",
    "meta",
    "db",
])
