# -*- coding: utf-8 -*-
#
# petition/views.py
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

from django.http import HttpResponse, HttpResponseRedirect, HttpResponsePermanentRedirect, Http404
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib import auth
from django.core.mail import send_mail
from django.template import Context
from django.template.loader import get_template
from django.db import connection
from django.views.decorators.cache import never_cache
from django.contrib.auth.models import User
from re import match
from time import strftime, time, localtime
from datetime import datetime
from socket import gethostbyaddr
from bs4 import BeautifulSoup
from xml.sax.saxutils import escape
from petition.forms import PetitionForm, SignatureForm
from petition.data.models import Petition, Signature

APP = 'petition'

VERSION = '1.0'

URL_BASE = 'petice.pecina.cz'
BATCH = 100

def cb2s(c):
    if c:
        return 'ano'
    else:
        return 'ne'

def oe(n):
    if n % 2:
        return 'odd'
    else:
        return 'even'

def norm(x, batch=BATCH):
    return (x // batch) * batch

def gennav(off, total, prefix, suffix='',
           batch=BATCH,
           i0='&lt;&lt;', i1='&lt;', i2='&gt;', i3='&gt;&gt;',
           a0='<a href="', a1='">', a2='</a>',
           g0='<span class="grayed">', g1='</span>',
           s0='', s1='&nbsp;&nbsp;', s2='&nbsp;&nbsp;<span class="pager">', s3='&nbsp;/&nbsp;', s4='</span>&nbsp;&nbsp;', s5='&nbsp;&nbsp;', s6=''):
    i = [i0, i1, i2, i3]
    n = [-1] * 4
    if off:
        n[0] = 0
        n[1] = off - batch
    if off + batch < total:
        n[2] = off + batch
        n[3] = norm(total - 1)
    p1 = (off // batch) + 1
    p2 = ((total - 1) // batch) + 1
    t = list(range(4))
    for j in range(4):
        if n[j] < 0:
            t[j] = g0 + i[j] + g1
        else:
            t[j] = a0 + prefix + str(n[j]) + suffix + a1 + i[j] + a2
    return s0 + t[0] + s1 + t[1] + s2 + str(p1) + s3 + str(p2) + s4 + t[2] + s5 + t[3] + s6

def error(request):
    var = {'page_title': 'Interní chyba aplikace', 'suppress_topline': True}
    return render(request, 'error.html', var)

def unauth(request):
    var = {'page_title': 'Neoprávněný přístup'}
    return render(request, 'unauth.html', var)

def mainpage(request):
    return HttpResponseRedirect('/admin/petitionlist/')

def redir(request, par):
    return HttpResponsePermanentRedirect('http://www.pecina.cz/petice/' + par)

def newXML(data):
    xml = BeautifulSoup(data, 'lxml')
    xml.is_xml = True
    return xml

def xmldecorate(tag, table):
    if table.has_key(tag.name):
        for key, val in table[tag.name].items():
            tag[key] = val
    return tag

def xmlescape(t):
    return escape(t).strip()

def view(request, name=''):
    fields = ['longname', 'keywords', 'css', 'text', 'counter', 'closed']
    sfields = ['name', 'address', 'address_hidden', 'occupation', 'occupation_hidden', 'birthdate', 'birthdate_hidden', 'email', 'email_hidden', 'note', 'note_hidden']
    var = {'display_stat': True, 'display_thankyou': False, 'errors': False}
    if name:
        p = Petition.objects.filter(name=name)
    else:
        host = request.META.get('HTTP_HOST')
        if host == URL_BASE:
            return mainpage(request)
        p = Petition.objects.filter(domain=host)
    if not p:
        raise Http404()
    p = p[0]
    if not name:
        name = ''
    var['id'] = name
    var['page_title'] = p.longname
    var['total'] = p.signature_set.count()
    if request.method == 'GET':
        thankyou = request.GET.get('thankyou')
        if not thankyou:
            cursor = connection.cursor()
            cursor.execute(('update data_petition set counter=counter+1 where id=%u' % p.id), [])
        for t in fields:
            var[t] = p.__getattribute__(t)
        closed = var['closed']
        var['display_form'] = (not (thankyou or closed))
        var['display_closed'] = closed
        var['display_thankyou'] = thankyou
    elif request.method == 'POST':
        if p.closed:
            return error(request)
        f = SignatureForm(request.POST)
        if f.is_valid():
            cd = f.cleaned_data
            cd['ip'] = request.META.get('REMOTE_ADDR').split(',')[0]
            try:
                cd['domain'] = gethostbyaddr(cd['ip'])[0]
            except:
                cd['domain'] = cd['ip']
            cd['petition_id'] = p.id
            s = Signature(**cd)
            if s.save():
                return error(request)
            else:
                return HttpResponseRedirect('/%s/?thankyou=1' % name)
        var['errors'] = True
        for t in fields:
            var[t] = p.__getattribute__(t)
        for t in sfields:
            var[t] = request.POST.get(t)
            if f[t].errors:
                var[t + '_error'] = 'err'
            else:
                var[t + '_error'] = 'ok'
        var['display_form'] = True
    else:
        return error(request)
    return render(request, 'petitionbody.html', var)

@login_required
def petitionform(request, id=0):
    u = request.user
    uid = u.id
    fields = ['name', 'domain', 'email', 'closed', 'longname', 'keywords', 'css', 'text']
    var = {'url_base': URL_BASE, 'errors': False}
    if request.method == 'GET':
        if id:
            p = Petition.objects.filter(pk=id)
            if not p:
                return error(request)
            p = p[0]
            if p.user_id != uid and not u.is_superuser:
                return unauth(request)
            var.update({'id': id, 'page_title': 'Úprava petice'})
            for t in fields:
                var[t] = p.__getattribute__(t)
                var[t + '_error'] = 'ok'
        else:
            var.update({'id': 0, 'page_title': 'Nová petice'})
            for t in fields:
                var[t + '_error'] = 'ok'
    elif request.method == 'POST':
        if not id:
            id = 0
        f = PetitionForm(request.POST)
        if f.is_valid():
            cd = f.cleaned_data
            if cd['id']:
                p = Petition.objects.filter(pk=cd['id'])
                if not p:
                    return error(request)
                p = p[0]
                if p.user_id != uid and not u.is_superuser:
                    return unauth(request)
                cd['user'] = p.user
                cd['timestamp'] = p.timestamp
                cd['counter'] = p.counter
            else:
                del cd['id']
                cd['user'] = u
                cd['counter'] = 0
            p = Petition(**cd)
            if p.save():
                return error(request)
            else:
                return mainpage(request)
        else:
            var.update({'errors': True, 'id': id})
            if id:
                var['page_title'] = 'Úprava petice'
            else:
                var['page_title'] = 'Nová petice'
            for t in fields:
                var[t] = request.POST.get(t)
                if f[t].errors:
                    var[t + '_error'] = 'err'
                else:
                    var[t + '_error'] = 'ok'
    else:
        return error(request)
    return render(request, 'petitionform.html', var)

@login_required
def petitionlist(request):
    u = request.user
    uid = u.id
    fields = ['id', 'user', 'name', 'domain', 'longname']
    var = {'page_title': 'Přehled petic', 'superuser': u.is_superuser, 'rows': []}
    if u.is_superuser:
        p = Petition.objects.all().order_by('timestamp')
    else:
        p = Petition.objects.filter(user=uid).order_by('timestamp')
    n = 0
    for row in p:
        r = {}
        for t in fields:
            r[t] = row.__getattribute__(t)
        r['timestamp'] = row.timestamp.strftime('%d.%m.%Y')
        r['closed'] = cb2s(row.closed)
        n += 1
        r['number'] = n
        r['class'] = oe(n)
        r['total'] = row.signature_set.count()
        var['rows'].append(r)
    return render(request, 'petitionlist.html', var)

@login_required
def petitiondetail(request, id=0):
    u = request.user
    uid = u.id
    fields = ['id', 'name', 'domain', 'email', 'longname', 'keywords', 'counter']
    var = {'url_base': URL_BASE, 'page_title': 'Podrobnosti o petici'}
    p = Petition.objects.filter(pk=id)
    if not p:
        return error(request)
    p = p[0]
    if p.user_id != uid and not u.is_superuser:
        return unauth(request)
    for t in fields:
        var[t] = p.__getattribute__(t)
    var['timestamp'] = p.timestamp.strftime('%d.%m.%Y %H:%M:%S')
    var['closed'] = cb2s(p.closed)
    var['len_css'] = len(p.css)
    var['len_text'] = len(p.text)
    var['total'] = p.signature_set.count()
    return render(request, 'petitiondetail.html', var)

@login_required
def petitiondel(request, id=0):
    u = request.user
    uid = u.id
    var = {'page_title': 'Smazání petice'}
    if request.method == 'GET':
        p = Petition.objects.filter(pk=id)
        if not p:
            return error(request)
        p = p[0]
        if p.user_id != uid and not u.is_superuser:
            return unauth(request)
        var['id'] = id
        var['longname'] = p.longname
        var['total'] = p.signature_set.count()
        return render(request, 'petitiondel.html', var)
    elif request.method == 'POST':
        if request.POST.get('del') == 'Ano':
            p = Petition.objects.filter(pk=id)
            if not p:
                return error(request)
            p = p[0]
            if p.user_id != uid and not u.is_superuser:
                return unauth(request)
            p.delete()
        return mainpage(request)
    else:
        return error(request)

@login_required
def signaturelist(request, id=0, off=0):
    u = request.user
    uid = u.id
    fields = ['id', 'name', 'occupation', 'occupation_hidden', 'birthdate_hidden', 'address', 'address_hidden', 'email', 'email_hidden', 'note', 'note_hidden']
    var = {'page_title': 'Přehled podpisů', 'petition_id': id, 'rows': []}
    if off:
        off = int(off)
    else:
        off = 0
    p = Petition.objects.filter(pk=id)
    if not p:
        return error(request)
    p = p[0]
    if p.user_id != uid and not u.is_superuser:
        return unauth(request)
    total = p.signature_set.count()
    if off >= total:
        off = norm(total - 1)
    if total:
        s = p.signature_set.order_by('-timestamp')[off:off+BATCH]
        n = off
        for row in s:
            r = {}
            for t in fields:
                r[t] = row.__getattribute__(t)
            r['timestamp'] = row.timestamp.strftime('%d.%m.%Y %H:%M')
            try:
                r['birthdate'] = row.birthdate.strftime('%d.%m.%Y')
            except:
                r['birthdate'] = ''
            n += 1
            r['number'] = n
            r['class'] = oe(n)
            var['rows'].append(r)
        var['nav'] = gennav(off, total, ('/admin/signaturelist/%s/' % id))
    var['total'] = total
    var['off'] = off
    var['petition_longname'] = p.longname
    return render(request, 'signaturelist.html', var)

def slist(request):
    fields = ['name', 'occupation', 'occupation_hidden', 'address', 'address_hidden', 'email', 'email_hidden', 'note', 'note_hidden']
    var = {'page_title': 'Seznam podpisů', 'rows': []}
    name = request.GET.get('id','')
    off = int(request.GET.get('off', 0))
    filt = request.GET.get('filter', '')
    if name:
        p = Petition.objects.filter(name=name)
    else:
        p = Petition.objects.filter(domain=request.META.get('HTTP_HOST'))
    if not p:
        return error(request)
    p = p[0]
    if filt:
        total = p.signature_set.filter(name__search=(filt + '*')).count()
    else:
        total = p.signature_set.count()
    if off >= total:
        off = norm(total - 1)
    if total:
        if filt:
            s = p.signature_set.filter(name__search=(filt + '*')).order_by('timestamp')[off:off+BATCH]
        else:
            s = p.signature_set.order_by('timestamp')[off:off+BATCH]
        n = off
        for row in s:
            r = {}
            for t in fields:
                r[t] = row.__getattribute__(t)
            r['timestamp'] = row.timestamp.strftime('%d.%m.%Y %H:%M')
            if row.birthdate and not row.birthdate_hidden:
                r['birthdate'] = row.birthdate.strftime('%d.%m.%Y')
            else:
                r['birthdate'] = ''
            n += 1
            r['number'] = n
            r['class'] = oe(n)
            var['rows'].append(r)
        var['nav'] = gennav(off, total, ('/list/?id=%s&amp;filter=%s&amp;off=' % (name, filt)))
    if name:
        var['url'] = '/%s/' % name
    else:
        var['url'] = '/'
    var['id'] = name
    var['total'] = total
    var['off'] = off
    var['filter'] = filt
    var['petition_longname'] = p.longname
    return render(request, 'list.html', var)

@login_required
def signaturedetail(request, id=0):
    u = request.user
    uid = u.id
    fields = ['id', 'name', 'occupation', 'address', 'email', 'note', 'ip', 'domain']
    checkboxes = ['occupation_hidden', 'address_hidden', 'birthdate_hidden', 'email_hidden', 'note_hidden', 'reported']
    var = {'page_title': 'Podrobnosti o podpisu'}
    s = Signature.objects.filter(pk=id)
    if not s:
        return error(request)
    s = s[0]
    p = Petition.objects.filter(pk=s.petition_id)
    if not p:
        return error(request)
    p = p[0]
    if p.user_id != uid and not u.is_superuser:
        return unauth(request)
    for t in fields:
        var[t] = s.__getattribute__(t)
    for t in checkboxes:
        var[t] = cb2s(s.__getattribute__(t))
    if s.birthdate:
        var['birthdate'] = s.birthdate.strftime('%d.%m.%Y')
    var['timestamp'] = s.timestamp.strftime('%d.%m.%Y %H:%M:%S')
    var['petition_longname'] = p.longname
    return render(request, 'signaturedetail.html', var)

@login_required
def signaturedel(request):
    u = request.user
    uid = u.id
    if request.method == 'POST':
        b = request.POST.get('del')
        if b.startswith('Smazat'):
            var = {'page_title': 'Smazání podpisů', 'rows': []}
            for t in request.POST:
                if match(r'del\d+$',t):
                    var['rows'].append(t)
            n = len(var['rows'])
            if n == 1:
                en = ''
            elif n < 5:
                en = 'y'
            else:
                en = 'ů'
            var['total'] = n
            var['total_ending'] = en
            var['petition_id'] = request.POST.get('petition_id')
            var['off'] = request.POST.get('off')
            return render(request, 'signaturedel.html', var)
        if b == 'Ano':
            for t in request.POST:
                if match(r'del\d+$',t):
                    s = Signature.objects.filter(pk=t[3:])
                    if not s:
                        return error(request)
                    s = s[0]
                    p = Petition.objects.filter(pk=s.petition_id)
                    if not p:
                        return error(request)
                    p = p[0]
                    if p.user_id != uid and not u.is_superuser:
                        return unauth(request)
                    s.delete()
        return HttpResponseRedirect('/admin/signaturelist/%s/%s/' % (request.POST.get('petition_id'), request.POST.get('off')))
    else:
        return error(request)

@login_required
def logout(request):
    var = {'page_title': 'Odhlášení', 'suppress_topline': True}
    auth.logout(request)
    return render(request, 'logout.html', var)

@login_required
def pwchange(request):
    var = {'page_title': 'Změna hesla'}
    u = request.user
    uid = u.id
    if request.method == 'POST':
        fields = ['oldpw', 'newpw1', 'newpw2']
        for f in fields:
            var[f] = request.POST.get(f, '')
        if not u.check_password(var['oldpw']):
            var['error_message'] = 'Nesprávné heslo'
            var['oldpw'] = ''
        elif var['newpw1'] != var['newpw2']:
            var['error_message'] = 'Zadaná hesla se neshodují'
            var['newpw1'] = var['newpw2'] = ''
        elif len(var['newpw1']) < 6:
            var['error_message'] = 'Nové heslo je příliš krátké'
            var['newpw1'] = var['newpw2'] = ''
        else:
            u.set_password(var['newpw1'])
            u.save()
            return mainpage(request)
    elif request.method == 'GET':
        pass
    else:
        return error(request)
    return render(request, 'pwchange.html', var)

def robots(request):
    return render(request, 'robots.txt', content_type='text/plain; charset=utf-8')

@never_cache
def cron(request):
    cursor = connection.cursor()
    cursor.execute("select email from data_petition where email <> %s and closed = %s group by email", ['', '0'])
    emails = cursor.fetchall()
    for e in emails:
        e = e[0]
        petitions = []
        for p in Petition.objects.filter(email=e, closed=False).order_by('pk'):
            b = {'longname': p.longname, 'total': p.signature_set.count(), 'signatures': []}
            sign = p.signature_set.filter(reported=False)
            for s in sign:
                b['signatures'].append({'name': s.name, 'occupation': s.occupation, 'address': s.address, 'note': s.note})
            petitions.append(b)
        t = get_template('email.tpl')
        o = t.render(request, Context({'url': ('http://%s/' % URL_BASE), 'time': strftime('%d.%m.%Y %H:%M:%S'), 'petitions': petitions}))
        if send_mail('Denni zprava aplikace Petice', o, 'Robot <no-reply@pecina.cz>', [e]):
            for p in Petition.objects.filter(email=e):
                p.signature_set.update(reported=True)
    return HttpResponse('')

@login_required
def export(request, id):
    u = request.user
    uid = u.id
    var = {'page_title': 'Export seznamu podpisů do souboru', 'id': id, 
           'formats': [
               {'format': 'csvutf_8', 'desc': 'Soubor CSV (UTF-8)', 'newgroup': False},
               {'format': 'csvcp1250', 'desc': 'Soubor CSV (CP1250/Windows)', 'newgroup': False},
               {'format': 'csvcp852', 'desc': 'Soubor CSV (CP852/Latin 2)', 'newgroup': False},
               {'format': 'csviso8859_2', 'desc': 'Soubor CSV (ISO 8859-2/Latin 2)', 'newgroup': False},
               {'format': 'csvmac_latin2', 'desc': 'Soubor CSV (Mac CE)', 'newgroup': False},
               {'format': 'csvascii', 'desc': 'Soubor CSV (ASCII bez diakritiky)', 'newgroup': False},
               {'format': 'xml', 'desc': 'Soubor XML', 'newgroup': True},
               {'format': 'yaml', 'desc': 'Soubor YAML', 'newgroup': False},
               {'format': 'pdf', 'desc': 'Soubor PDF', 'newgroup': False},
          ]}
    p = Petition.objects.filter(pk=id)
    if not p:
        return error(request)
    p = p[0]
    if p.user_id != uid and not u.is_superuser:
        return unauth(request)
    var['petition_longname'] = p.longname
    return render(request, 'export.html', var)

@login_required
def doexport(request, id):
    u = request.user
    uid = u.id
    fields = ['address', 'occupation', 'email', 'note']
    showall = request.GET.get('all')
    format = request.GET.get('format', 'csvutf-8')
    header = request.GET.get('header')
    semicol = request.GET.get('semicol')
    p = Petition.objects.filter(pk=id)
    if not p:
        return error(request)
    p = p[0]
    if p.user_id != uid and not u.is_superuser:
        return unauth(request)
    s = p.signature_set.order_by('timestamp')
    if not s:
        return HttpResponseRedirect('/admin/petitionlist/')
    if format[:3] == 'csv':
        import csv
        from io import StringIO
        asciitbl=str.maketrans('áäčďéěëíĺľňóôöŕřšťúůüýžÁÄČĎÉĚËÍĹĽŇÓÔÖŔŘŠŤÚŮÜÝŽ','aacdeeeillnooorrstuuuyzAACDEEEILLNOOORRSTUUUYZ')
        def rawascii(l):
            return l.translate(asciitbl).encode('ascii', 'replace')
        enc = format[3:]
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=podpisy.csv'
        if semicol:
            delimiter = ';'
        else:
            delimiter = ','
        sio = StringIO()
        writer = csv.writer(sio, delimiter=delimiter)
        if header:
            hl = ['Jméno a příjmení', 'Adresa', 'Povolání', 'Datum narození', 'E-mail', 'Poznámka', 'Datum a čas podpisu']
            writer.writerow(hl)
        for row in s:
            r = {}
            for f in fields:
                if showall or not row.__getattribute__(f + '_hidden'):
                    r[f] = row.__getattribute__(f)
                else:
                    r[f] = ''
            if row.birthdate and (showall or not row.birthdate_hidden):
                bd = row.birthdate.strftime('%d.%m.%Y')
            else:
                bd = ''
            if row.timestamp:
                ts = row.timestamp.strftime('%d.%m.%Y %H:%M')
            else:
                ts = ''
            w = [row.name, r['address'], r['occupation'], bd, r['email'], r['note'], ts]
            writer.writerow(w)
        sio.seek(0)
        u = sio.read()
        if enc == 'ascii':
            b = rawascii(u)
        else:
            b = u.encode(enc, 'replace')
        response.write(b)
        return response
    elif format == 'xml':
        xd = {'petition': {
            'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
            'xsi:noNamespaceSchemaLocation': 'http://petice.pecina.cz/static/%s-%s.xsd' % (APP, VERSION),
                'application': APP,
                'version': VERSION,
                'created': datetime.now().replace(microsecond=0).isoformat()
            }
        }
        xml = newXML('')
        d = xmldecorate(xml.new_tag('petition'), xd)
        xml.append(d)
        tag = xml.new_tag('name')
        tag.append(xmlescape(p.longname))
        d.append(tag)
        sg = xml.new_tag('signatures')
        for ss in s:
            t = xml.new_tag('signature')
            tag = xml.new_tag('name')
            tag.append(xmlescape(ss.name))
            t.append(tag)
            for f in ['address', 'birthdate', 'occupation', 'email', 'note']:
                if (showall or not ss.__getattribute__(f + '_hidden')) and ss.__getattribute__(f):
                    tag = xml.new_tag(f)
                    if f == 'birthdate':
                        tag.append(ss.birthdate.isoformat())
                    else:
                        tag.append(xmlescape(ss.__getattribute__(f)))
                    if showall:
                        tag['hidden'] = str(ss.__getattribute__(f + '_hidden')).lower()
                    t.append(tag)
            if ss.birthdate and (showall or not ss.birthdate_hidden):
                tag = xml.new_tag('timestamp')
                tag.append(ss.timestamp.isoformat())
                t.append(tag)
            sg.append(t)
        d.append(sg)
        response = HttpResponse(content_type='text/xml')
        response['Content-Disposition'] = 'inline; filename=export.xml'
        response.write(str(xml).encode('utf-8') + '\n')
        return response
    elif format == 'yaml':
        var = {'longname': p.longname, 'rows': []}
        var['timestamp'] = strftime('%Y-%m-%d %H:%M:%S', localtime(time()))
        for row in s:
            r = {}
            r['name'] = row.name
            for f in fields:
                if showall or not row.__getattribute__(f + '_hidden'):
                    r[f] = row.__getattribute__(f)
            if row.birthdate and (showall or not row.birthdate_hidden):
                r['birthdate'] = row.birthdate.strftime('%Y-%m-%d')
            r['timestamp'] = row.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            var['rows'].append(r)
        return render(request, 'export.yml', var, content_type='text/yaml')
    elif format == 'pdf':
        import reportlab.rl_config
        from reportlab.pdfbase.pdfmetrics import registerFont, registerFontFamily
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import Paragraph, SimpleDocTemplate, LongTable, TableStyle
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_RIGHT
        from reportlab.lib.pagesizes import A4
        from io import BytesIO
        import os.path
        fontdir = os.path.join(os.path.dirname(__file__), 'fonts/').replace('\\','/')
        def page1(c, d):
            c.saveState()
            c.setFont('Liberation-Sans', 7)
            c.drawCentredString((A4[0] / 2), 30, ('Strana %u' % d.page))
            c.restoreState()
        def page2(c, d):
            page1(c, d)
            c.saveState()
            c.setFont('Liberation-SansB', 8)
            c.drawCentredString((A4[0] / 2), (A4[1] - 50), p.longname)
            c.restoreState()
        def sanitize(text, limit):
            l = text.split(' ')
            for i in range(len(l)):
                if len(l[i]) > limit:
                    l[i] = l[i][:limit] + u'…'
            return ' '.join(l)
        reportlab.rl_config.warnOnMissingFontGlyphs = 0
        registerFont(TTFont('Liberation-Sans', (fontdir + 'LiberationSans-Regular.ttf')))
        registerFont(TTFont('Liberation-SansB', (fontdir + 'LiberationSans-Bold.ttf')))
        registerFont(TTFont('Liberation-SansI', (fontdir + 'LiberationSans-Italic.ttf')))
        registerFont(TTFont('Liberation-SansBI', (fontdir + 'LiberationSans-BoldItalic.ttf')))
        registerFontFamily('Liberation-Sans', normal='Liberation-Sans', bold='Liberation-SansB', italic='Liberation-SansI', boldItalic='Liberation-SansBI')
        sh1 = ParagraphStyle(name='Heading1', fontName='Liberation-SansB', fontSize=12, leading=14, spaceAfter=0, alignment=TA_CENTER)
        sh2 = ParagraphStyle(name='Heading2', fontName='Liberation-SansI', fontSize=8, leading=10, spaceBefore=0, spaceAfter=9, alignment=TA_CENTER)
        sth = ParagraphStyle(name='TableHeading', fontName='Liberation-SansB', fontSize=5, leading=6, textColor='#ffffff', alignment=TA_CENTER)
        stcl = ParagraphStyle(name='TableContentsLeft', fontName='Liberation-Sans', fontSize=5, leading=6)
        stcc = ParagraphStyle(name='TableContentsCenter', fontName='Liberation-Sans', fontSize=5, leading=6, alignment=TA_CENTER)
        sno = ParagraphStyle(name='Notice', fontName='Liberation-SansI', fontSize=5, leading=6, spaceBefore=9, alignment=TA_RIGHT, rightIndent=-6)
        flow = [Paragraph(p.longname, sh1)]
        flow.append(Paragraph(('Počet podpisů: %u' % s.count()), sh2))
        th = ['Pořadí', 'Datum a čas', 'Jméno a příjmení', 'Povolání', 'Adresa', 'Narozen/a', 'E-mail', 'Poznámka']
        data = [[Paragraph(x, sth) for x in th]]
        n = 0
        for row in s:
            n += 1
            r = {}
            for f in fields:
                if showall or not row.__getattribute__(f + '_hidden'):
                    r[f] = row.__getattribute__(f)
                else:
                    r[f] = ''
            if row.birthdate and (showall or not row.birthdate_hidden):
                birthdate = row.birthdate.strftime('%d.%m.%Y')
            else:
                birthdate = ''
            data.append([
                    Paragraph(str(n), stcc),
                    Paragraph(row.timestamp.strftime('%d.%m.%Y %H:%M'), stcc),
                    Paragraph(sanitize(row.name, 20), stcl),
                    Paragraph(sanitize(r['occupation'], 20), stcl),
                    Paragraph(sanitize(r['address'], 30), stcl),
                    Paragraph(birthdate, stcc),
                    Paragraph(sanitize(r['email'].lower(), 30), stcl),
                    Paragraph(sanitize(r['note'], 45), stcl),
                    ])
        t = LongTable(data, colWidths=[22.15, 46.10, 52.95, 52.95, 76.65, 30.35, 80.50, 120.25], repeatRows=1)
        t.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), '#000000'),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), ['#FFFFFF', '#F0F0F0']),
                    ('ALIGN', (0,0), (-1,0), 'CENTER'),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('LEFTPADDING', (0,0), (-1,-1), 2),
                    ('RIGHTPADDING', (0,0), (-1,-1), 2),
                    ('TOPPADDING', (0,0), (-1,-1), 2),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 2),
                    ]))
        flow.append(t)
        flow.append(Paragraph(strftime('Vytvořeno: %d.%m.%Y %H:%M:%S', localtime(time())), sno))
        temp = BytesIO()
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename=export.pdf'
        doc = SimpleDocTemplate(
            temp,
            pagesize=A4,
            title='Seznam podpisů',
            leftMargin=56.7,
            rightMargin=56.7,
            topMargin=56.7,
            bottomMargin=56.7,
            )
        doc.build(flow, onFirstPage=page1, onLaterPages=page2)
        response.write(temp.getvalue())
        return response
    else:
        return error(request)
