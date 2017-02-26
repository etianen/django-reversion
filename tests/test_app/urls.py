from django.conf.urls import url
from test_app import views


urlpatterns = [
    url("^save-obj/", views.save_obj_view),
    url("^save-obj-error/", views.save_obj_error_view),
    url("^is-atomic/", views.is_atomic_view),
    url("^create-revision/", views.create_revision_view),
    url("^atomic-revision/", views.atomic_revision_view),
    url("^non-atomic-revision/", views.non_atomic_revision_view),
    url("^revision-mixin/", views.RevisionMixinView.as_view()),
    url("^revision-mixin-atomic/", views.RevisionMixinAtomicView.as_view()),
    url("^revision-mixin-non-atomic/", views.RevisionMixinNonAtomicView.as_view()),
]
