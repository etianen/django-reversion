from django.http import HttpResponse
from django.views.generic.base import View
from reversion.views import RevisionMixin
from test_app.models import ReversionTestModel1


class SaveRevisionViewBase(View):

    def dispatch(self, request):
        ReversionTestModel1.objects.create(
            name="model1 instance3 version1",
        )
        return HttpResponse("OK")


class SaveRevisionView(RevisionMixin, SaveRevisionViewBase):

    pass


class ErrorRevisionViewBase(View):

    def dispatch(self, request):
        ReversionTestModel1.objects.create(
            name="model1 instance1 version1",
        )
        raise Exception("Boom!")


class ErrorRevisionView(RevisionMixin, ErrorRevisionViewBase):

    pass
