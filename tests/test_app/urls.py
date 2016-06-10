from django.conf.urls import url
from test_app import views


urlpatterns = [
    url("^save-obj/", views.save_obj_view),
    url("^save-obj-error/", views.save_obj_error_view),
    url("^create-revision/", views.create_revision_view),
    url("^revision-mixin/", views.RevisionMixinView.as_view()),
]
