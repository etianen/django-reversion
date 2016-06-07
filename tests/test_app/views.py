from django.http import HttpResponse
from django.views.generic.base import View
from reversion.views import create_revision, RevisionMixin
from test_app.models import TestModel


def save_obj_view(request):
    return HttpResponse(TestModel.objects.create().id)


@create_revision()
def create_revision_view(request):
    return save_obj_view(request)


class RevisionMixinView(RevisionMixin, View):

    def dispatch(self, request):
        return save_obj_view(request)
