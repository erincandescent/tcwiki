# -*- coding: utf-8 -*-
from django.conf.urls.defaults import *
from views import *
urlpatterns = patterns('',
    url(r'^$', page, name='wiki-home'),
    url(r'^([a-zA-Z_/ ]+)$', page, name='wiki-page'),
)