from django.conf.urls import url

from landscapesim.tiles.views import GetImageView, GetTimeSeriesImageView

SERVICE_REGEX = r'(?P<service_name>[a-f0-9]{8}-?[a-f0-9]{4}-?4[a-f0-9]{3}-?[89ab][a-f0-9]{3}-?[a-f0-9]{12})'

urlpatterns = [
    url(
        r'^tiles/' + SERVICE_REGEX + '/(?P<z>\d+)/(?P<x>\d+)/(?P<y>\d+).png$', GetImageView.as_view(),
        name='tiles_get_image'
    ),
    url(
        r'^tiles/' + SERVICE_REGEX + '/(?P<layer_name>[a-z][a-z_]*(\-\d+)+)/(?P<z>\d+)/(?P<x>\d+)/(?P<y>\d+)/(?P<t>\d+).png$',
        GetTimeSeriesImageView.as_view(),
        name='timeseries_tiles_get_image'
    )
]
