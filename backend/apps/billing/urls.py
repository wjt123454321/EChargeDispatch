from django.urls import path

from . import views

urlpatterns = [
    path('bill/list', views.bill_list),
    path('bill/detail/<int:bill_id>', views.bill_detail),
    path('bill/pay/<int:bill_id>', views.bill_pay),
]
