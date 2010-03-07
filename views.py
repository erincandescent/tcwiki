# -*- coding: utf-8 -*-
import difflib
from models import *
from django.http import *
from django.template import RequestContext
from django.template.loader import *
from django.shortcuts import *
from django.core.urlresolvers import reverse
from django.contrib.auth.views import redirect_to_login
from django.views.decorators.cache import cache_control
from django.core.cache import cache
from creoleparser.core import Parser
from creoleparser.dialects import create_dialect, creole11_base

def _gen_link(name, wiki_info):
    name = canonicalize_name(name)
    pageloc = wiki_info['pageloc']
    if page_exists(name):
        return pageloc(name)
    else:
        return pageloc(name) + '?a=edit'

parsers = {}
def get_parser(wiki_info):
    parser = None
    if wiki_info['wiki_id'] in parsers:
        parser = parsers[wiki_info['wiki_id']]
    else:
        parser = Parser(create_dialect(
            creole11_base,
            wiki_links_base_url   = '',
            wiki_links_space_char = '_',
            wiki_links_class_func = (lambda p: '' if page_exists(wiki_id, p) else 'create'),
            wiki_links_path_func  = (lambda n: _gen_link(n, wiki_info))
        ), 'xhtml', True, 'utf-8')
        parsers[wiki_info['wiki_id']] = parser
    return parser

def page_exists(wiki_info, name):
    try:
        Page.objects.get(wiki_id = wiki_info['wiki_id'], name = canonicalize_name(name))
        return True
    except Page.DoesNotExist, e:
        return False

def canonicalize_name(name):
    name = name.replace(' ', '_')
    name = name[0].upper() + name[1:]
    return name

def render_markup(markup, wiki_info):
    return get_parser(wiki_info).render(markup)

def render_page(rev, wiki_info):
    key = 'wiki-page-%d-%d' % (wiki_info['wiki_id'], rev.id)
    val = cache.get(key)
    if not val:
        val = render_markup(rev.content, wiki_info)
        cache.set(key, val)
    return val

def merge(d1, d2):
    d1.update(d2)
    return d1

default_wiki = {
    'pageloc': lambda page: reverse('wiki-page', args=[page]),
    'wiki_id': 1,
    'context': {},
}

@cache_control(must_revalidate=True)
def page(request, name="Main_page", wiki_info=default_wiki):
    wiki_id = wiki_info['wiki_id']
    pageloc = wiki_info['pageloc']
    context = wiki_info['context']

    if name.find(' ') != -1 or name[0].upper() != name[0]:
        query = '?' + request.META['QUERY_STRING'] if 'QUERY_STRING' in request.META else ''
        return HttpResponseRedirect(pageloc(canonicalize_name(name)) + query)
    action   = request.REQUEST['a'].lower() if 'a' in request.REQUEST else 'view'
    title    = name.replace('_', ' ')
    page = False
    revision = 0
    oldrev = False

    try:
        page = Page.objects.get(wiki_id = wiki_id, name = name)
    except Page.DoesNotExist, e:
        pass

    if page:
        if 'rev' in request.GET and len(request.GET['rev']) <> 0:
            revision = page.revision_set.get(pk = int(request.GET['rev']))
            newest = page.revision_set.order_by('-pk')[0]
            oldrev = revision.pk != newest.pk
        else:
            revision = page.revision_set.order_by('-pk')[0]
            
    if action == 'view':
        if page:
            return render_to_response("TCWiki/page.html", merge({
                'name':        name,
                'title':       title,
                'content':     render_page(revision, wiki_info),
                'revision':    revision,
                'oldrev':      oldrev,
                'wiki':        wiki_info,
            }, context), context_instance=RequestContext(request))
        else:
            return HttpResponseNotFound(render_to_string("TCWiki/page404.html", merge({
                'name':  name,
                'title': title,
                'wiki': wiki_info,
            }, context), context_instance=RequestContext(request)))
    elif action == 'edit' or action == "preview":
        if not request.user.is_authenticated():
            return redirect_to_login(request.path + '?a=edit')

        if not request.user.has_perm('TCWiki.change_page'):
            return render_to_response("TCWiki/denied.html", merge({ 
                'name': name, 
                'title': title,
                'wiki': wiki_info,
            }, context), context_instance=RequestContext(request))

        preview = False
        comment = ''
        if 'content' in request.POST:
            markup  = request.POST['content']
            comment = request.POST['comment']
            preview = render_markup(markup, wiki_info)
        elif revision:
            markup = revision.content
        else:
            markup = ''

        return render_to_response("TCWiki/edit.html", merge({
            'name':        name,
            'title':       title,
            'preview':     preview,
            'markup':      markup,
            'oldrev':      oldrev,
            'revision':    revision,
            'wiki':        wiki_info,
        }, context), context_instance=RequestContext(request))
    elif action == 'history':
        if not page:
            raise Http404()

        if not request.user.has_perm('TCWiki.history'):
            return render_to_response("TCWiki/denied.html", merge({ 
                'name':  name, 
                'title': title,
                'wiki':  wiki_info,
            }, context), context_instance=RequestContext(request))

        revisions = page.revision_set.order_by('-pk').all()

        return render_to_response("TCWiki/history.html", merge({
            'name':      name,
            'title':     title,
            'revisions': revisions,
            'wiki':      wiki_info,
        }, context), context_instance=RequestContext(request))

    elif action == 'compare':
        if not page:
            raise Http404()

        if not request.user.has_perm('TCWiki.history'):
            return render_to_response("TCWiki/denied.html", merge({ 
                'name':  name, 
                'title': title,
                'wiki':  wiki_info,
            }, context), context_instance=RequestContext(request))

        cRev = page.revision_set.get(pk = int(request.GET['to']))
      
        fromLines = revision.content.splitlines()
        toLines = cRev.content.splitlines()

        diff = difflib.HtmlDiff()
        tbl = diff.make_table(fromLines, toLines, 'From', 'To')

        return render_to_response("TCWiki/compare.html", merge({
            'name':     name,
            'title':    title,
            'fromRev':  revision,
            'toRev':    cRev,
            'diff':     tbl.replace(' nowrap="nowrap"', '').replace('&nbsp;', ' '),
            'wiki':     wiki_info,
       }, context), context_instance=RequestContext(request))
    elif action == 'save':
        if not request.user.is_authenticated():
            return redirect_to_login(request.path)

        if not request.user.has_perm('TCWiki.change_page'):
            return render_to_response("TCWiki/denied.html", merge({ 
            'name':  name, 
            'title': title,
            'wiki':  wiki_info,
        }, context), context_instance=RequestContext(request))

        if not page:
            page = Page(name = name, wiki_id = wiki_id)
            page.save()

        revision = page.revision_set.create(author = request.user, content = request.POST['content'], comment = request.POST['comment'])
        revision.save()

        return HttpResponseRedirect(pageloc(name))

    elif action == 'dbg-perm':
        return HttpResponse(request.user.get_all_permissions())

    else:
        raise Http404()


