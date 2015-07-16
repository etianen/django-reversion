from django.contrib import admin

import reversion

from test_reversion.models import (
    ChildTestAdminModel,
    StrictChildTestAdminModel,
    InlineTestChildModel,
    InlineTestParentModel,
    InlineTestUnrelatedChildModel,
    InlineTestUnrelatedParentModel,
)


site = admin.AdminSite()


class ChildTestAdminModelAdmin(reversion.VersionAdmin):

    pass


site.register(ChildTestAdminModel, ChildTestAdminModelAdmin)


class StrictChildTestAdminModelAdmin(reversion.VersionAdmin):

    strict_revert = True  # Enable strict admin revert/restore


site.register(StrictChildTestAdminModel, StrictChildTestAdminModelAdmin)


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
