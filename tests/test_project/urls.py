from django.conf.urls import url, include
from django.contrib import admin

admin.autodiscover()

urlpatterns = [

    url(r"^admin/", admin.site.urls),

    url(r"^test-app/", include("test_app.urls")),

]
