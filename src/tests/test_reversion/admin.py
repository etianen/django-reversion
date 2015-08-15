from django.contrib import admin
try:
    from django.contrib.contenttypes.admin import GenericTabularInline
except ImportError:  # Django < 1.9  pragma: no cover
    from django.contrib.contenttypes.generic import GenericTabularInline

import reversion

from test_reversion.models import (
    ChildTestAdminModel,
    InlineTestChildModel,
    InlineTestParentModel,
    InlineTestUnrelatedChildModel,
    InlineTestUnrelatedParentModel,
    InlineTestChildGenericModel,
)


class ChildTestAdminModelAdmin(reversion.VersionAdmin):

    pass


admin.site.register(ChildTestAdminModel, ChildTestAdminModelAdmin)


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


class InlineTestParentModelAdmin(reversion.VersionAdmin):

    inlines = (InlineTestChildModelInline, InlineTestChildGenericModelInline)


admin.site.register(InlineTestParentModel, InlineTestParentModelAdmin)


class InlineTestUnrelatedChildModelInline(admin.TabularInline):

    model = InlineTestUnrelatedChildModel


class InlineTestUnrelatedParentModelAdmin(reversion.VersionAdmin):

    inlines = (InlineTestUnrelatedChildModelInline,)


admin.site.register(InlineTestUnrelatedParentModel, InlineTestUnrelatedParentModelAdmin)
