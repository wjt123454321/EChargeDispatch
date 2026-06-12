from django.urls import path

from . import views

urlpatterns = [
    path('admin/fault/report', views.fault_report),
    path('admin/fault/recover', views.fault_recover),
    path('admin/fault/list', views.fault_list),
    path('admin/report/stats', views.report_stats),
    path('admin/acceptance/snapshot', views.acceptance_snapshot),
]
