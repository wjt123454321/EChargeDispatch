from django.urls import path

from . import views

urlpatterns = [
    path('admin/system-config', views.system_config),
    path('pile/status', views.pile_status),
    path('pile/<int:pile_id>/poweron', views.pile_poweron),
    path('pile/<int:pile_id>/start', views.pile_start),
    path('pile/<int:pile_id>/poweroff', views.pile_poweroff),
]
