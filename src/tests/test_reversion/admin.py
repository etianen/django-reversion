from django.contrib import admin
try:
    from django.contrib.contenttypes.admin import GenericTabularInline
except ImportError:  # Django < 1.9  pragma: no cover
    from django.contrib.contenttypes.generic import GenericTabularInline

from reversion.admin import VersionAdmin

from test_reversion.models import (
    ChildTestAdminModel,
    InlineTestChildModel,
    InlineTestChildModelProxy,
    InlineTestParentModel,
    InlineTestParentModelProxy,
    InlineTestUnrelatedChildModel,
    InlineTestUnrelatedParentModel,
    InlineTestChildGenericModel,
    ReversionTestModel1,
    ReversionTestModel1Proxy,
    TestFollowModel,
    TestFollowModelProxy,
)


class ChildTestAdminModelAdmin(VersionAdmin):

    pass


admin.site.register(ChildTestAdminModel, ChildTestAdminModelAdmin)


class InlineTestChildModelProxyInline(admin.TabularInline):

    model = InlineTestChildModelProxy

    extra = 0

    verbose_name = "Proxy child"

    verbose_name_plural = "Proxy children"


class InlineTestChildModelInline(admin.TabularInline):

    model = InlineTestChildModel

    extra = 0

    verbose_name = "Child"

    verbose_name_plural = "Children"


class InlineTestChildGenericModelInline(GenericTabularInline):

    model = InlineTestChildGenericModel

    ct_field = "content_type"

    ct_fk_field = "object_id"

    extra = 0


class InlineTestParentModelAdmin(VersionAdmin):

    inlines = (InlineTestChildModelInline, InlineTestChildGenericModelInline,)


admin.site.register(InlineTestParentModel, InlineTestParentModelAdmin)


class InlineTestParentModelProxyAdmin(VersionAdmin):

    inlines = (InlineTestChildModelProxyInline,)


admin.site.register(InlineTestParentModelProxy, InlineTestParentModelProxyAdmin)


class InlineTestUnrelatedChildModelInline(admin.TabularInline):

    model = InlineTestUnrelatedChildModel


class InlineTestUnrelatedParentModelAdmin(VersionAdmin):

    inlines = (InlineTestUnrelatedChildModelInline,)


admin.site.register(InlineTestUnrelatedParentModel, InlineTestUnrelatedParentModelAdmin)

# Issue 465
from reversion import revisions
revisions.register(TestFollowModel)
revisions.register(ReversionTestModel1)


class TestFollowModelProxyAdmin(admin.TabularInline):
    model = TestFollowModelProxy
    fields = ('name',)


class ReversionTestModel1ProxyAdmin(VersionAdmin):
    inlines = [TestFollowModelProxyAdmin]

admin.site.register(ReversionTestModel1Proxy, ReversionTestModel1ProxyAdmin)
