from django.conf.urls import url
from test_app import views


urlpatterns = [
    url("^test/", views.test_view),
    url("^test-revision/", views.test_revision_view),
    url("^test-revision-cls/", views.TestRevisionView.as_view()),
]
