from django.urls import path

from .views import RailSathiAPI, RoRailSathiAPI

urlpatterns = [
    path('get/<int:complain_id>', RailSathiAPI.as_view(), name='get-rail-sathi-complain-by-id'),
    path('get/<str:date>', RailSathiAPI.as_view(), name='get-rail-sathi-complain-by-date'),
    path('add/', RailSathiAPI.as_view(), name='add-rail-sathi-complain'),
    path('patch/<int:complain_id>', RailSathiAPI.as_view(), name='partial-update-rail-sathi-complain'),
    path('update/<int:complain_id>', RailSathiAPI.as_view(), name='update-rail-sathi-complain'),
    path('delete/<int:complain_id>', RailSathiAPI.as_view(), name='delete-rail-sathi-complain'),
    path('delete-image/<int:complain_id>', RailSathiAPI.as_view(), name='delete-image-rail-sathi-complain'),
    
    # Unsecured URK for ro.suvidhaen.com
    path('ro/get/<int:complain_id>', RoRailSathiAPI.as_view(), name='ro-get-rail-sathi-complain-by-id'),
    path('ro/get/<str:date>', RoRailSathiAPI.as_view(), name='ro-get-rail-sathi-complain-by-date'),
    path('ro/add/', RoRailSathiAPI.as_view(), name='ro-add-rail-sathi-complain'),
    path('ro/patch/<int:complain_id>', RoRailSathiAPI.as_view(), name='ro-partial-update-rail-sathi-complain'),
    path('ro/update/<int:complain_id>', RoRailSathiAPI.as_view(), name='ro-update-rail-sathi-complain'),
    # Delete Endpoints are not available for ro.suvidhaen.com for now
    # path('ro/delete/<int:complain_id>', RoRailSathiAPI.as_view(), name='ro-delete-rail-sathi-complain'),
    # path('ro/delete-image/<int:complain_id>', RoRailSathiAPI.as_view(), name='ro-delete-image-rail-sathi-complain'),
]