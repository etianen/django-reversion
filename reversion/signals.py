from django.dispatch.dispatcher import Signal


pre_revision_commit = Signal(providing_args=["instances", "revision", "versions"])
post_revision_commit = Signal(providing_args=["instances", "revision", "versions"])
