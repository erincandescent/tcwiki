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

@cache_control(must_revalidate=True)
def page(request, name="Main_page"):
    if name.find(' ') != -1 or name[0].upper() != name[0]:
	query = '?' + request.META['QUERY_STRING'] if 'QUERY_STRING' in request.META else ''
	return HttpResponseRedirect(reverse('wiki-page', args=[canonicalize_name(name)]) + query)
    action   = request.REQUEST['a'].lower() if 'a' in request.REQUEST else 'view'
    title    = name.replace('_', ' ')
    page = False
    revision = False
    oldrev = False

    try:
	page = Page.objects.get(name = name)
    except Page.DoesNotExist, e:
	pass

    if page:
	if 'rev' in request.GET:
	    revision = page.revision_set.get(pk = int(request.GET['rev']))
	    newest = page.revision_set.order_by('-pk')[0]
	    oldrev = revision.pk != newest.pk
	else:
	    revision = page.revision_set.order_by('-pk')[0]
	    

    if action == 'view':
	if page:
	    return render_to_response("TCWiki/page.html", {
		'name':     name,
		'title':    title,
		'content':  revision.html,
		'revision': revision,
		'oldrev':   oldrev
	    }, context_instance=RequestContext(request))
	else:
	    return HttpResponseNotFound(render_to_string("TCWiki/page404.html", {
		'name':  name,
		'title': title
	    }, context_instance=RequestContext(request)))

    elif action == 'edit' or action == "preview":
	if not request.user.is_authenticated():
	    return redirect_to_login(request.path + '?a=edit')

	if not request.user.has_perm('TCWiki.change_page'):
	    return render_to_response("TCWiki/denied.html", { 'name': name, 'title': title}, context_instance=RequestContext(request))

	preview = False
	comment = ''
	if 'content' in request.POST:
	    markup  = request.POST['content']
	    comment = request.POST['comment']
	    preview = parser.render(markup)
	elif revision:
	    markup = revision.content
	else:
	    markup = ''

	return render_to_response("TCWiki/edit.html", {
	    'name':	name,
	    'title':	title,
	    'preview':  preview,
	    'markup':	markup,
	    'oldrev':	oldrev,
	    'revision':	revision,
	}, context_instance=RequestContext(request))

    elif action == 'history':
	if not page:
	    raise Http404()

	if not request.user.has_perm('TCWiki.history'):
	    return render_to_response("TCWiki/denied.html", { 'name': name, 'title': title}, context_instance=RequestContext(request))

	revisions = page.revision_set.order_by('-pk').all()

	return render_to_response("TCWiki/history.html", {
	    'name':      name,
	    'title':     title,
	    'revisions': revisions
	}, context_instance=RequestContext(request))

    elif action == 'compare':
      if not page:
	  raise Http404()

      if not request.user.has_perm('TCWiki.history'):
	  return render_to_response("TCWiki/denied.html", { 'name': name, 'title': title}, context_instance=RequestContext(request))

      cRev = page.revision_set.get(pk = int(request.GET['to']))
      
      fromLines = revision.content.splitlines()
      toLines = cRev.content.splitlines()

      diff = difflib.HtmlDiff()
      tbl = diff.make_table(fromLines, toLines, 'From', 'To')

      return render_to_response("TCWiki/compare.html", {
	    'name':	name,
	    'title':	title,
	    'fromRev':  revision,
	    'toRev':    cRev,
	    'diff':     tbl.replace(' nowrap="nowrap"', '').replace('&nbsp;', ' '),
      }, context_instance=RequestContext(request))

    elif action == 'save':
	if not request.user.is_authenticated():
	    return redirect_to_login(request.path)

	if not request.user.has_perm('TCWiki.change_page'):
	    return render_to_response("TCWiki/denied.html", { 'name': name, 'title': title}, context_instance=RequestContext(request))

	if not page:
	    page = Page(name = name)
	    page.save()

	revision = page.revision_set.create(author = request.user, content = request.POST['content'], comment = request.POST['comment'])
	revision.save()

	return HttpResponseRedirect(reverse('wiki-page', args=[name]))

    elif action == 'dbg-perm':
	return HttpResponse(request.user.get_all_permissions())

    else:
	raise Http404()