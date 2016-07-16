# -*- coding: utf-8 -*-
#
# petition/forms.py
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

from django import forms
from petition.data.models import Petition, Signature

class PetitionForm(forms.Form):
    id = forms.IntegerField(widget=forms.HiddenInput, required=False)
    name = forms.RegexField(max_length=30, regex=r'^[a-z][a-z0-9\-_]*$')
    domain = forms.RegexField(max_length=255, regex=r'^[a-z0-9\-]+(\.[a-z0-9\-]+)*(:\d+)?$', required=False)
    email = forms.EmailField(required=False)
    closed = forms.BooleanField(required=False)
    longname = forms.CharField(max_length=255)
    keywords = forms.CharField(max_length=255, required=False)
    css = forms.CharField(widget=forms.Textarea, required=False)
    text = forms.CharField(widget=forms.Textarea)

    def clean_name(self):
        name = self.cleaned_data['name']
        p = Petition.objects.filter(name=name)
        if p and p[0].id != self.cleaned_data['id']:
            raise forms.ValidationError("Duplicate name")
        return name

    def clean_domain(self):
        domain = self.cleaned_data['domain']
        if domain:
            p = Petition.objects.filter(domain=domain)
            if p and p[0].id != self.cleaned_data['id']:
                raise forms.ValidationError("Duplicate domain")
        return domain

class SignatureForm(forms.Form):
    name = forms.CharField(max_length=30)
    occupation = forms.CharField(max_length=255, required=False)
    occupation_hidden = forms.BooleanField(required=False)
    address = forms.CharField(max_length=255)
    address_hidden = forms.BooleanField(required=False)
    birthdate = forms.DateField(widget=forms.DateInput, required=False, input_formats=['%d.%m.%Y'])
    birthdate_hidden = forms.BooleanField(required=False)
    email = forms.EmailField(required=False)
    email_hidden = forms.BooleanField(required=False)
    note = forms.CharField(widget=forms.Textarea, required=False)
    note_hidden = forms.BooleanField(required=False)

    def clean_name(self):
        name = self.cleaned_data['name']
        if 'http://' in name:
            raise forms.ValidationError("Link in field")
        return name

    def clean_occupation(self):
        occupation = self.cleaned_data['occupation']
        if 'http://' in occupation:
            raise forms.ValidationError("Link in field")
        return occupation

    def clean_address(self):
        address = self.cleaned_data['address']
        if 'http://' in address:
            raise forms.ValidationError("Link in field")
        return address

    def clean_note(self):
        note = self.cleaned_data['note']
        if 'http://' in note:
            raise forms.ValidationError("Link in field")
        return note
