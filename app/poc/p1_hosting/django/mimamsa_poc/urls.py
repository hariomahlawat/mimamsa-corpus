from django.urls import path
from . import views

urlpatterns = [
    path("health", views.health),
    path("api/search", views.search),
    path("api/documents/<str:doc_id>", views.document),
    path("api/documents/<str:doc_id>/pdf", views.pdf),
]
