from django.dispatch.dispatcher import Signal


# Version management signals.
pre_revision_commit = Signal(providing_args=["instances", "revision", "versions"])
post_revision_commit = Signal(providing_args=["instances", "revision", "versions"])
