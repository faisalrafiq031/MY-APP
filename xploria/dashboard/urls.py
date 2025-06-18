from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('', views.home, name='home'),
    path('tables/', views.tables, name='tables'),
    path('query-editor/', views.query_editor, name='query_editor'),
    path('designer/', views.designer, name='designer'),
    path('analytics/', views.analytics, name='analytics'),
    path('get-columns/', views.get_columns, name='get_columns'),
]

# Serve static and media files during development

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)