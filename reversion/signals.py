from django.dispatch.dispatcher import Signal


_signal_args = [
    "revision",
    "versions",
]

pre_revision_commit = Signal(providing_args=_signal_args)
post_revision_commit = Signal(providing_args=_signal_args)
