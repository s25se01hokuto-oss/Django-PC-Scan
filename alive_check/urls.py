from django.urls import path
from .views import seat_map_view

urlpatterns = [
    path('', seat_map_view, name='seat_map'),  # Route root path of alive_check to seat_map_view
]
