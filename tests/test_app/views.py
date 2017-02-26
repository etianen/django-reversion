from django.db.transaction import get_connection
from django.http import HttpResponse
from django.views.generic.base import View
from reversion.views import create_revision, RevisionMixin
from test_app.models import TestModel


def save_obj_view(request):
    return HttpResponse(TestModel.objects.create().id)


def save_obj_error_view(request):
    TestModel.objects.create()
    raise Exception("Boom!")


@create_revision()
def create_revision_view(request):
    return save_obj_view(request)


def _is_atomic_view():
    return HttpResponse(get_connection().in_atomic_block)


@create_revision(atomic=True)
def atomic_revision_view(request):
    return _is_atomic_view()


@create_revision(atomic=False)
def non_atomic_revision_view(request):
    return _is_atomic_view()


class RevisionMixinView(RevisionMixin, View):

    def dispatch(self, request):
        return save_obj_view(request)


class RevisionMixinAtomicView(RevisionMixin, View):
    revision_atomic = True

    def dispatch(self, request):
        return _is_atomic_view()


class RevisionMixinNonAtomicView(RevisionMixinAtomicView):
    revision_atomic = False
