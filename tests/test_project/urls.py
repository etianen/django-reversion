from django.conf.urls import include
from django.urls import path
from django.contrib import admin

admin.autodiscover()

urlpatterns = [

    path("admin/", admin.site.urls),
    path("test-app/", include("test_app.urls")),

]
