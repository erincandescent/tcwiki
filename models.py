# -*- coding: utf-8 -*-
from django.db import models
from django.contrib.auth.models import User


class Page(models.Model):
    wiki_id = models.PositiveSmallIntegerField(default=1)
    name    = models.CharField(max_length=100)

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

