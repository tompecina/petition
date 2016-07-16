# -*- coding: utf-8 -*-
#
# petition/data/models.py
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

from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Petition(models.Model):
    user = models.ForeignKey(User)
    name = models.CharField(max_length=30, unique=True)
    domain = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    closed = models.BooleanField()
    longname = models.CharField(max_length=255)
    keywords = models.CharField(max_length=255, blank=True)
    css = models.TextField(blank=True)
    text = models.TextField()
    counter = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return self.longname

class Signature(models.Model):
    petition = models.ForeignKey(Petition)
    name = models.CharField(max_length=30, db_index=True)
    occupation = models.CharField(max_length=255, blank=True)
    occupation_hidden = models.BooleanField()
    address = models.CharField(max_length=255)
    address_hidden = models.BooleanField()
    birthdate = models.DateField(blank=True, null=True)
    birthdate_hidden = models.BooleanField()
    email = models.EmailField(blank=True)
    email_hidden = models.BooleanField()
    note = models.TextField(blank=True)
    note_hidden = models.BooleanField()
    ip = models.GenericIPAddressField()
    domain = models.CharField(max_length=255)
    reported = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return self.name
