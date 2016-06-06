from reversion.views import create_revision, RevisionMixin
from test_app.models import TestModel


def test_view(request):
    TestModel.objects.create()
