from django.conf.urls import patterns, url, include

from test_reversion import views
from test_reversion.admin import site


urlpatterns = patterns("",

    url("^success/$", views.save_revision_view),

    url("^error/$", views.error_revision_view),

    url("^double/$", views.double_middleware_revision_view),

    url("^admin/", include(site.get_urls(), namespace="admin")),

)
