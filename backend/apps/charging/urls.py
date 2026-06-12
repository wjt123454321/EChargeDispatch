from django.urls import path

from . import views

urlpatterns = [
    path('charging/request', views.submit_request),
    path('charging/amount', views.update_amount),
    path('charging/mode', views.update_mode),
    path('charging/queue-status', views.queue_status),
    path('charging/start', views.start_charging),
    path('charging/status', views.charging_status),
    path('charging/end', views.end_charging),
    path('charging/cancel', views.cancel_charging),
    path('queue/pile/<int:pile_id>', views.pile_queue),
]
