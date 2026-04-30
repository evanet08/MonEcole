from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve
from django.views.generic.base import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='login', permanent=False)),
    path('admin/', admin.site.urls),
    path('', include('MonEcole_app.urls')),
    # Serve media files (evaluations, photos, etc.) - works with gunicorn
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    # PWA assets — served from root for proper SW scope
    path('manifest.json', serve, {'document_root': settings.BASE_DIR / 'MonEcole_app' / 'static', 'path': 'manifest.json'}),
    path('sw.js', serve, {'document_root': settings.BASE_DIR / 'MonEcole_app' / 'static', 'path': 'sw.js'}),
]
