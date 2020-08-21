from django.urls import path
from test_app import views


urlpatterns = [
    path("save-obj/", views.save_obj_view),
    path("save-obj-error/", views.save_obj_error_view),
    path("create-revision/", views.create_revision_view),
    path("revision-mixin/", views.RevisionMixinView.as_view()),
]
