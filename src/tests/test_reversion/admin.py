from django.contrib import admin

import reversion

from test_reversion.models import (
    ChildTestAdminModel,
    InlineTestChildModel,
    InlineTestParentModel,
    InlineTestUnrelatedChildModel,
    InlineTestUnrelatedParentModel,
)


site = admin.AdminSite()


class ChildTestAdminModelAdmin(reversion.VersionAdmin):

    pass


site.register(ChildTestAdminModel, ChildTestAdminModelAdmin)


class InlineTestChildModelInline(admin.TabularInline):

    model = InlineTestChildModel

    fk_name = "parent"

    extra = 0

    verbose_name = "Child"

    verbose_name_plural = "Children"


class InlineTestParentModelAdmin(reversion.VersionAdmin):

    inlines = (InlineTestChildModelInline,)


site.register(InlineTestParentModel, InlineTestParentModelAdmin)


class InlineTestUnrelatedChildModelInline(admin.TabularInline):

    model = InlineTestUnrelatedChildModel


class InlineTestUnrelatedParentModelAdmin(reversion.VersionAdmin):

    inlines = (InlineTestUnrelatedChildModelInline,)


site.register(InlineTestUnrelatedParentModel, InlineTestUnrelatedParentModelAdmin)
