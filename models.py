# -*- coding: utf-8 -*-
from django.db import models
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.urlresolvers import reverse
from creoleparser.core import Parser
from creoleparser.dialects import create_dialect, creole11_base

def _gen_link(name):
    name = canonicalize_name(name)
    if page_exists(name):
	return reverse('wiki-page', args=[name])
    else:
	return reverse('wiki-page', args=[name]) + '?a=edit'

parser = Parser(create_dialect(
    creole11_base,
    wiki_links_base_url   = '',
    wiki_links_space_char = '_',
    wiki_links_class_func = (lambda p: '' if page_exists(p) else 'create'),
    wiki_links_path_func  = _gen_link
), 'xhtml', True, 'utf-8')

def page_exists(name):
    try:
	Page.objects.get(name = canonicalize_name(name))
	return True
    except Page.DoesNotExist, e:
	return False

def canonicalize_name(name):
    name = name.replace(' ', '_')
    name = name[0].upper() + name[1:]
    return name

class Page(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
	permissions = (
            ("history", "Can view history"),
        )

class Revision(models.Model):
    page    = models.ForeignKey(Page)
    author  = models.ForeignKey(User)
    date    = models.DateTimeField(auto_now_add=True)
    comment = models.CharField(max_length=140)
    content = models.TextField()

    @property
    def html(self):
	key = 'htmlrev' + str(self.id)
	val = cache.get(key)
	if not val:
	    val = parser.render(self.content)
	    cache.set(key, val)
	return val

