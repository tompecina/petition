# -*- coding: utf-8 -*-
#
# petition/urls.py
#
# Copyright (C) 2011-16 Tomáš Pecina <tomas@pecina.cz>
#
# This file is part of petition.pecina.cz, a web-based petition
# application.
#
# This application is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This application is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.         
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from django.conf.urls import url, include
from django.contrib.auth.views import login, settings
from .views import petitionform, petitionlist, petitiondetail, petitiondel, \
                   signaturelist, slist, signaturedetail, signaturedel, \
                   export, doexport, pwchange, logout, view, redir, robots, cron

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

settings.LOGIN_URL = '/admin/login/'
settings.LOGOUT_URL = '/admin/logout/'

urlpatterns = [
    url(r'^admin/petitionform/((?P<id>\d+)/)?$',
        petitionform,
        name='petitionform'),
    url(r'^admin/petitionlist/$',
        petitionlist,
        name='petitionlist'),
    url(r'^admin/petitiondetail/(?P<id>\d+)/$',
        petitiondetail,
        name='petitiondetail'),
    url(r'^admin/petitiondel/(?P<id>\d+)/$',
        petitiondel,
        name='petitiondel'),
    url(r'^admin/signaturelist/(?P<id>\d+)/((?P<off>\d+)/)?$',
        signaturelist,
        name='signaturelist'),
    url(r'^list/$',
        slist,
        name='slist'),
    url(r'^admin/signaturedetail/(?P<id>\d+)/$',
        signaturedetail,
        name='signaturedetail'),
    url(r'^admin/signaturedel/$',
        signaturedel,
        name='signaturedel'),
    url(r'^admin/export/(?P<id>\d+)/$',
        export,
        name='export'),
    url(r'^admin/doexport/(?P<id>\d+)/$',
        doexport,
        name='doexport'),
    url(r'^admin/pwchange/$',
        pwchange,
        name='pwchange'),
    url(r'^admin/logout/$',
        logout,
        name='logout'),
    url(r'robots.txt$',
        robots),
    url(r'^admin/cron-fb3316fef6d425dce6f23821fa027b74/$',
        cron),
    url(r'^admin/login/$',
        login,
        {'template_name': 'login.html'},
        name='login'),
    url(r'^admin/',
        include(admin.site.urls)),
    url(r'^((?P<name>[a-z][a-z0-9\-_]*)/)?$',
        view,
        name='view'),
    url(r'^(?P<par>.*\..*)$',
        redir,
        name='redir'),
]
