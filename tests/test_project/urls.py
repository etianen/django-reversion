from django.conf.urls import include, url
from django.contrib import admin
from test_app import views


urlpatterns = [

    url(r'^admin/', include(admin.site.urls)),

    url(r"^success-base/$", views.SaveRevisionViewBase.as_view()),
    url(r"^success/$", views.SaveRevisionView.as_view()),

    url(r"^error-base/$", views.ErrorRevisionViewBase.as_view()),
    url(r"^error/$", views.ErrorRevisionView.as_view()),

]
