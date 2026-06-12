from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.accounts.urls')),
    path('api/', include('apps.charging.urls')),
    path('api/', include('apps.station.urls')),
    path('api/', include('apps.billing.urls')),
    path('api/', include('apps.operations.urls')),
]
