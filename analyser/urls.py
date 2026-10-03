from django.urls import path
from . import views


urlpatterns = [
    path("", views.home_view, name="home"),
    path("delete/<int:pk>/", views.delete_dataset, name="delete_dataset"),
    path("analyze/<int:pk>/", views.analyze_dataset, name="analyze"),
    path("preview/<int:pk>/", views.preview_dataset, name="preview"),
]