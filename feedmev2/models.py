# -*- coding: utf-8 -*-

from django.db import models
from django.contrib.auth.models import Group
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()
#User = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')

class Order(models.Model):
    date = models.DateField(_("date"))

    def get_total_sum(self):
        return self.orderline_set.aggregate(models.Sum('price'))

    def order_users(self):
        return User.objects.filter(groups__name=settings.FEEDME_GROUP)

    def taken_users(self):
        return self.orderline_set.values_list('creator', flat=True)

    def __unicode__(self):
        return self.date.strftime("%d-%m-%Y")

    class Meta:
        get_latest_by = 'date'

class OrderLine(models.Model):
    order = models.ForeignKey(Order)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='Owner')
    buddy_system = models.BooleanField(_('Enable buddy system', default=False))
    #users = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name=_('buddies'), null=True, blank=True)
    menu_item = models.IntegerField(_('menu item'), max_length=2, default=8)
    soda = models.CharField(_('soda'), blank=True, null=True, default='cola', max_length=25)
    extras = models.CharField(_('extras/comments'), blank=True, null=True, max_length=50)
    price = models.IntegerField(_('price'), max_length=4, default=100)

    def get_order(self):
        return self.order

    def __unicode__(self):
        return self.creator.username

    @models.permalink
    def get_absolute_url(self):
        return ('edit', (), {'orderline_id' : self.id})

    class Meta:
        verbose_name = _('Order line')
        verbose_name_plural = _('Order lines')

class Funds(models.Model):
    funds = models.FloatField(_('funds'), default=0)
    user = models.ForeignKey(settings.AUTH_USER_MODEL)

class ManageOrders(models.Model):
    orders = models.OneToOneField(Order, related_name=_('Orders'))

class ManageUsers(models.Model):
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name=_('Users'))

class ManageOrderLimit(models.Model):
    order_limit = models.IntegerField(_('Order limit'), default=100)

class Restaurant(models.Model):
    name = models.CharField(_('name'), max_length=50)
    menu_url = models.CharField(_('menu url'), max_length=250)
    phone_number = models.CharField(_('phone number'), max_length=15)
    email = models.EmailField(_('email address'), blank=True, null=True)