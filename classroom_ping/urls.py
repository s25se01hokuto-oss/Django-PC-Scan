from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('alive_check.urls')),  # Route root URL to the alive_check application
    path('alive_check/', include('alive_check.urls')),  # Route /alive_check/ path as well
]
