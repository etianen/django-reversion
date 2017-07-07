from django.contrib import admin
from reversion.admin import VersionAdmin
from test_app.models import TestModel, TestModelRelated


class TestModelAdmin(VersionAdmin):

    filter_horizontal = ("related",)


admin.site.register(TestModel, TestModelAdmin)


admin.site.register(TestModelRelated, admin.ModelAdmin)
