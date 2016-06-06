from django.http import HttpResponse
from django.views.generic.base import View
from reversion.views import create_revision, RevisionMixin
from test_app.models import TestModel


def test_view(request):
    return HttpResponse(TestModel.objects.create().id)


@create_revision()
def test_revision_view(request):
    return test_view(request)


class TestRevisionView(RevisionMixin, View):

    def dispatch(self, request):
        return test_view(request)
