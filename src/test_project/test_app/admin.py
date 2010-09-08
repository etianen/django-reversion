from django.contrib import admin
from django.contrib.contenttypes.generic import GenericStackedInline

from reversion.admin import VersionAdmin


from test_project.test_app.models import ChildModel, RelatedModel, GenericRelatedModel, ProxyModel


class RelatedModelInline(admin.StackedInline):
    
    model = RelatedModel
    
    
class GenericRelatedInline(GenericStackedInline):
    
    model = GenericRelatedModel
    
    
class ChildModelAdmin(VersionAdmin):
    
    inlines = RelatedModelInline, GenericRelatedInline,
    
    list_display = ("parent_name", "child_name",)
    
    list_editable = ("child_name",)
    
    
admin.site.register(ChildModel, ChildModelAdmin)


admin.site.register(ProxyModel, ChildModelAdmin)

