from django.contrib import admin
try:
    from django.contrib.contenttypes.admin import GenericInlineModelAdmin
except ImportError:  # Django < 1.9  pragma: no cover
    from django.contrib.contenttypes.generic import GenericInlineModelAdmin

import reversion

from test_reversion.models import (
    ChildTestAdminModel,
    InlineTestChildModel,
    InlineTestParentModel,
    InlineTestUnrelatedChildModel,
    InlineTestUnrelatedParentModel,
    InlineTestChildGenericModel,
)


site = admin.AdminSite()


class ChildTestAdminModelAdmin(reversion.VersionAdmin):

    pass


site.register(ChildTestAdminModel, ChildTestAdminModelAdmin)


class InlineTestChildModelInline(admin.TabularInline):

    model = InlineTestChildModel

    extra = 0

    verbose_name = "Child"

    verbose_name_plural = "Children"


class InlineTestChildGenericModelInline(GenericInlineModelAdmin):

    model = InlineTestChildGenericModel

    ct_field = "content_type"

    ct_fk_field = "object_id"


class InlineTestParentModelAdmin(reversion.VersionAdmin):

    inlines = (InlineTestChildModelInline, InlineTestChildGenericModelInline)


site.register(InlineTestParentModel, InlineTestParentModelAdmin)


class InlineTestUnrelatedChildModelInline(admin.TabularInline):

    model = InlineTestUnrelatedChildModel


class InlineTestUnrelatedParentModelAdmin(reversion.VersionAdmin):

    inlines = (InlineTestUnrelatedChildModelInline,)


site.register(InlineTestUnrelatedParentModel, InlineTestUnrelatedParentModelAdmin)
