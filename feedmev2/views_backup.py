from datetime import date, timedelta

from django.contrib import messages
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Sum

from feedmev2.models import OrderLine, Order, Funds, ManageOrderLimit
from forms import OrderLineForm, OrderForm,  ManageOrderForm, ManageOrderLimitForm, NewOrderForm, ManageUsersForm

User = get_user_model()

@user_passes_test(lambda u: u.groups.filter(name=settings.FEEDME_GROUP).count() == 1)
def index(request):
    order = get_order()
    return render(request, 'index.html', {'order_line' : order, 'is_admin' : is_admin(request)})

def orderlineview(request, orderline_id=None):
    if orderline_id == None:
        orderline = OrderLine()
    else:
        orderline = get_object_or_404(OrderLine, pk=orderline_id)

    if request.method == 'POST':
        form = OrderLineForm(request.POST, instance=orderline)
        if form.is_valid():
            form = form.save(commit=False)
            form.user = request.user
            form.order_line = get_order()

            if check_orderline(request, form, orderline_id):
                form.save()
                return redirect(index)
            else:
                form = OrderLineForm(request.POST, auto_id=True)
        else:
            form = OrderLineForm(request.POST, auto_id=True)
    else:
        if orderline_id:
            form = OrderLineForm(instance=orderline)
            #form.fields["users"].queryset = get_order().free_users(orderline.users, orderline.user)
        else:
            form = OrderLineForm(instance=orderline, initial={'buddy' : request.user})
            #form.fields["users"].queryset = get_order().order_users()

    return render(request, 'orderview.html', {'form' : form, 'is_admin' : is_admin(request)})

def edit_orderline(request, orderline_id):
    orderline = get_object_or_404(OrderLine, pk=orderline_id)
    if not is_in_current_order('orderline', orderline_id):
        messages.error(request, 'you can not edit orderlines from old orders')
    elif orderline.user != request.user:
        messages.error(request, 'You need to be the creator')
        return redirect(index)
    return orderlineview(request, orderline_id)

def delete_orderline(request, orderline_id):
    orderline = get_object_or_404(OrderLine, pk=orderline_id)
    if not is_in_current_order('orderline', orderline_id):
        messages.error(request, 'you can not delete orderlines from old orders')
    elif orderline.user == request.user:
        orderline.delete()
        messages.success(request,'Order line deleted')
    else:
        messages.error(request, 'You need to be the creator')
    return redirect(index)

@user_passes_test(lambda u: u.groups.filter(name=settings.FEEDME_GROUP).count() == 1)
def orderview(request, order_id=None):
    if order_id:
        order = get_object_or_404(Order, pk=order_id)
    else:
        order = Order()

    if request.method == 'POST':
        form = OrderForm(request.POST, instance=order)
        if form.is_valid():
            form = form.save(commit=False)
            form.user = request.user
            form.order_line = get_order()
            form.save()
            messages.success(request, 'Order added')
            return redirect(index)

        form = OrderForm(request.POST)
    else:
        form = OrderForm(instance=order)

    return render(request, 'orderview.html', {'form' : form, 'is_admin' : is_admin(request)})

def delete_order(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    if not is_in_current_order('order', order_id):
        messages.error(request, 'you can not delete orders from old orders')
    elif order.user == request.user:
        order.delete()
        messages.success(request,'Order deleted')
    else:
        messages.error(request, 'You need to be the creator')
    return redirect(index)


def edit_order(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    if not is_in_current_order('order', order_id):
        messages.error(request, 'you can not edit orders from old orders')
    elif order.user != request.user:
        messages.error(request, 'You need to be the creator to edit orders')
    else:
        return orderview(request, order_id)
    return redirect(index)

@user_passes_test(lambda u: u.groups.filter(name=settings.FEEDME_GROUP).count() == 1)
def join_orderline(request, orderline_id):
    orderline = get_object_or_404(OrderLine, pk=orderline_id)
    #if user_is_taken(request.user):
        #messages.error(request, 'You are already part of an order line')
    if not is_in_current_order('orderline', orderline_id):
        messages.error(request, 'You can not join orderlines from old orders')
    elif not orderline.need_buddy:
        messages.error(request, 'You can\'t join that order line')
    #elif not request.user.saldo_set.all():
    #    messages.error(request, 'No saldo connected to the user')
    #elif request.user.saldo_set.get().saldo < get_order_limit().order_limit:
    #    messages.error(request, 'You have insufficent funds. Current limit : ' + str(get_order_limit().order_limit))
    else:
        orderline.save()
        messages.success(request, 'Success!')
    return redirect(index)

# ADMIN

@user_passes_test(lambda u: u.groups.filter(name=settings.FEEDME_ADMIN_GROUP).count() == 1)
def new_order(request):
    if request.method == 'POST':
        form = NewOrderForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request,'New order line added')
            return redirect(new_order)
    else:
        form = NewOrderForm()
        form.fields["date"].initial = get_next_tuesday()

    return render(request, 'admin.html', {'form' : form })

@user_passes_test(lambda u: u.groups.filter(name=settings.FEEDME_ADMIN_GROUP).count() == 1)
def set_order_limit(request):
    limit = get_order_limit()
    if request.method == 'POST':
        form = ManageOrderLimitForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            limit.order_limit = data['order_limit']
            limit.save()
            messages.success(request,'Order limit changed')
            return redirect(set_order_limit)
    else:
        form = ManageOrderLimitForm(instance=limit)

    return render(request, 'admin.html', {'form' : form })

@user_passes_test(lambda u: u.groups.filter(name=settings.FEEDME_ADMIN_GROUP).count() == 1)
def manage_users(request):
    if request.method == 'POST':
        form = ManageUsersForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            handle_deposit(data)
            messages.success(request, 'Deposit successful')
            return redirect(manage_users)
    else:
        validate_saldo()
        form = ManageUsersForm()
        form.fields["users"].queryset = get_orderline_users()

    return render(request, 'admin.html', {'form' : form })

@user_passes_test(lambda u: u.groups.filter(name=settings.FEEDME_ADMIN_GROUP).count() == 1)
def manage_order(request):
    if request.method == 'POST':
        form = ManageOrderForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            handle_payment(request, data)
            return redirect(manage_order_lines)
        else:
            form = ManageOrderForm(request.POST)
    else:
        form = ManageOrderForm()

    unhandeled_orders = Order.objects.aggregate(Sum('orderline__price'))
    form.fields["orders"].queryset = unhandeled_orders
    return render(request, 'admin.html', {'form' : form, 'orders' : unhandeled_orders})

def get_order_limit():
    order_limit = ManageOrderLimit.objects.all()
    if order_limit:
        order_limit = ManageOrderLimit.objects.get(pk=1)
    else:
        order_limit = ManageOrderLimit()
    return order_limit

# @TODO Move logics to models

#def user_is_taken(user):
#    return user in get_order().used_users()

def check_orderline(request, form, orderline_id=None):
    #validate_saldo()
    order_limit = get_order_limit().order_limit
    funds = form.user.funds_set.get()

    messages.success(request, 'Order line added')
    return True # Removed logics

"""
    #if not orderline_id:
        #if user_is_taken(form.user):
        #    messages.error(request, form.user.username + ' has already ordered')
        #    return False
        if user_is_taken(form.buddy):
            messages.error(request, form.buddy.username + ' has already ordered')
            return False
    if form.user == form.buddy:
        if saldo.saldo < (order_limit * 2):
           messages.error(request, u'' + form.user.username + ' has insufficient funds. Current limit: ' + str(order_limit) )
           return False
    else:
        if saldo.saldo < order_limit:
            messages.error(request,u'' + form.user.username + ' has insufficient funds. Current limit: ' + str(order_limit) )
            return False

        saldo = form.buddy.saldo_set.get()
        if saldo.saldo < order_limit:
            messages.error(request,u'' + form.buddy.username + ' has insufficient funds. Current limit: ' + str(order_limit) )
            return False"""


def handle_payment(request, data):
    order_line = data['order_lines']
    total_sum = data['total_sum']
    users = order_line.used_users()
    if users:
        divided_sum = (total_sum / len(users)) * -1
        handle_saldo(users, divided_sum)
        order_line.total_sum = total_sum
        order_line.save()
        messages.success(request, 'Payment handeled')
    else:
        messages.error(request, 'Selected order contains no users')

def handle_deposit(data):
    users = data['users']
    deposit = data['add_value']

    handle_saldo(users, deposit)

def handle_saldo(users, value):
    for user in users:
        saldo = user.saldo_set.get()
        saldo.saldo += value
        saldo.save()

def validate_saldo():
    users = get_orderline_users()
    for user in users:
        funds = user.funds_set.all()
        if not funds:
            funds = Funds()
            funds.user = user
            funds.save()

def get_next_tuesday():
    today = date.today()
    day = today.weekday()
    if day < 1:
        diff = timedelta(days=(1 - day))
    elif day > 1:
        diff = timedelta(days=(7- day + 1))
    else:
        diff = timedelta(days=0)

    return today + diff

def is_admin(request):
    return request.user in User.objects.filter(groups__name=settings.FEEDME_ADMIN_GROUP)

def get_orderline_users():
   return User.objects.filter(groups__name=settings.FEEDME_GROUP)

def get_order():
    if Order.objects.all():
        return Order.objects.all().latest()
    else:
        return False

def is_in_current_order(order_type, order_id):
    order = get_order()
    if order_type == 'orderline':
        orderline = get_object_or_404(OrderLine, pk=order_id)
        return orderline in order.orderline_set.all()
    elif order_type == 'order':
        order = get_object_or_404(Order, pk=order_id)
        return order in order.order_set.all()
    else:
        return False