import json
from datetime import timedelta
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render, get_object_or_404
from django.http import HttpRequest, JsonResponse, HttpResponse
from .models import Category, ProductType, Item, CartItem, Cart, MyOrders, Attributes, Order, OrderItem, Review, UserDetails
from front_app_manager.models import FrontMedia
from django.db.models import Max
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib.auth import authenticate, login as login_dj
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import reverse
from django.db.models import Count, Q
from .utils import is_password_correct, update_instance, sent_order_email
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import stripe
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import update_session_auth_hash
import shippo
from ecommerce.goshippoapi import amount_from_rateid, purchase_shipment_rate, validate_address, get_shipping_rates
from front_app_manager.models import Partners, BestSellingProducts, OurMakingVideos


shippo.config.api_key = settings.SHIPPO_API_KEY
stripe.api_key = settings.STRIPE_SECRET_KEY

from_address_id = "13a1b287d150432896a25b04a6fc5d89"

COUNTRIES = ["US"]
country_map = {"GB": "United Kingdom", "US": "United States", "CA": "Canada"}
User = get_user_model()

@csrf_exempt
def checkout(request: HttpRequest):
    if request.method == 'POST':
        email = request.POST.get('email')
        contact_name = request.POST.get("contact_name")
        phone_number = request.POST.get("phone_number")
        country = request.POST.get('country')
        address1 = request.POST.get("address1")
        address2 = request.POST.get("address2")
        city = request.POST.get("city")
        state = request.POST.get("state")
        postal_code = request.POST.get("postal_code")
        try:
            address_id = validate_address(contact_name, email, address1, city, state, postal_code, country, address2)
            
        except Exception:
            messages.error(request, f"Address is incomplete or is invalid!")
            return render(request, 'checkout.html')
        
        try:
            user = User.objects.get(email=email)
        except ObjectDoesNotExist:
            user = None
        try:
            addr = UserDetails.objects.get(user=user)
        except ObjectDoesNotExist:
            addr = None
        if not user:
            user = User.objects.create_user(email=email, username=email, password=email, first_name=contact_name)
            user.save()
        if addr:
            addr.address_object_id=address_id
            addr.phone=phone_number
            addr.country=country
            addr.addr_line1=address1
            addr.addr_line2=address2
            addr.postal_code=postal_code
            addr.city=city
            addr.name=contact_name
            addr.state=state
            addr.save()
        else:
            UserDetails.objects.create(address_object_id=address_id, user=user, phone=phone_number, name=contact_name,
                                       country=country, addr_line1=address1, addr_line2=address2, postal_code=postal_code,
                                       city=city, state=state).save()

        if request.user.is_authenticated:
            current_cart = Cart.objects.filter(user=user).first()
            current_cart.save()
        else:
            old_cart = Cart.objects.filter(user=user) 
            if old_cart.exists():
                old_cart.delete()

            current_cart = Cart.objects.filter(session_key=request.session.session_key).first()
            current_cart.user = user
            current_cart.save()
        login_dj(request, user)
        messages.success(request, "Your account has been created! please change your password. your password is same as your email")
            
        return redirect('billing')

    if request.method == 'GET':
        email = ""
        if request.user.is_authenticated:
            email = request.user.email
        return render(request, "checkout.html", {"email": email})

@login_required
@csrf_exempt
def billing(request: HttpRequest):
    if request.method == 'POST':
        body_unicode = request.body.decode('utf-8')
        body = json.loads(body_unicode)
        shipping_rate_id = body.get('shippingRate')
        shipping_amount = amount_from_rateid(shipping_rate_id)
        
        total_amount = request.user.cart.get_total_amount() + shipping_amount
        total_amount_cents = int(round(total_amount, 2) * 100)
        try:
            checkout_session = stripe.checkout.Session.create(
            client_reference_id=request.user.id,
            success_url=settings.DOMAIN_URL + '/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=settings.DOMAIN_URL + '/cancel',
            payment_method_types=['card'],
            mode='payment',
            customer_email=request.user.email,
            automatic_tax={"enabled": False},
            line_items = [
                    {
                        'price_data': {
                            'currency': 'usd',
                            'unit_amount': int(total_amount_cents),
                            'product_data': {'name': "Your Order"},
                        },
                        'quantity': 1,
                    }
                ],
            metadata={"rate_id": shipping_rate_id, "shipping_rate_amount": shipping_amount, "total_amount": total_amount}
            )
            return JsonResponse({'sessionId': checkout_session['id']})
        
        except Exception as e:
            error_details = {
                'error_type': str(type(e).__name__),
                'error_message': str(e),
            }
            return JsonResponse({'error': str(error_details)})
    
    if request.method == 'GET':
        user = request.user
        try:
            user_address = user.userdetails
        except Exception:
            return redirect("checkout")

        if user_address:
            user_address_id = user_address.address_object_id
        else:
            return redirect("checkout")
        if user.cart:
            cart_items = user.cart.cart_items.all()
        else:
            return redirect("all_products")
        parcel_size = user.cart.get_parcel_size()
        tm = user.cart.get_total_amount()
        rates = get_shipping_rates(from_address_id, user_address_id, parcel_size)
        ship_amt = round(float(rates[0]["amount_local"]), 2)
        context = {"cart_items": cart_items, "rates": rates, "total_amount": f"{(tm + ship_amt):.2f}", 
                        "initial_cart_amount": tm}
        return render(request, 'billing.html', context)

@csrf_exempt
def stripe_webhook(request):
    endpoint_secret = settings.STRIPE_ENDPOINT_SECRET
    payload = request.body.decode('utf-8')
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        print("error1:", e)
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        print("SignatureVerificationError: ", e)
        return HttpResponse(status=400)
    if event['type'] == 'checkout.session.completed':
        user_id = int( event['data']["object"]["client_reference_id"] )
        rate_id = event['data']['object']['metadata']['rate_id']
        rate_amount = event['data']['object']['metadata']['shipping_rate_amount']
        total_amount = event['data']['object']['metadata']['total_amount']

        user = User.objects.get(id=user_id)
        user_address = user.userdetails
        order = Order.objects.create(user=user, email=user.email, contact_name=user_address.name, 
                                    goshippo_address_id=user_address.address_object_id, total_amount=f"{float(total_amount):.2f}",
                                    shipping_fee=f"{float(rate_amount):.2f}")
        order.save()
        MyOrders.objects.create(user=user, order=order).save()
        for carti in user.cart.cart_items.all():
            item = Item.objects.get(sku=carti.item_sku)
            item.quantity -= carti.quantity
            if item.quantity <= 0:
                item.sold_out = True
            item.save()
            order_item = OrderItem.objects.create(item_name=carti.item_name, item_price=carti.calculate_total_price(), variant=carti.variant,
                                          category=carti.item_category, product_type=carti.item_product_type, item_quantity=carti.quantity,
                                          order=order)
            order_item.save()
            carti.delete()
        try:
            tracking_url_provider, label_url = purchase_shipment_rate(rate_id)
            order.label_url = label_url
            order.tracking_url_provider = tracking_url_provider
            order.save()

        except Exception as e:
            print(e)

        sent_order_email(user.email, order, user_address.country)


    return HttpResponse(status=200)

@csrf_exempt
def set_timezone(request):
    if request.method == 'POST':
        try:
            utc_offset_minutes = request.POST.get('utc_offset_minutes')
            if utc_offset_minutes:
                request.session['user_timezone'] = utc_offset_minutes
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'error': 'Time zone not provided'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Error: {str(e)}'})

    return JsonResponse({'success': False, 'error': 'Invalid request method'})
def autocomplete_view(request: HttpRequest):
    if request.method == 'GET':
        query = request.GET.get('query', '')
        results = []
        if query:
            items = Item.objects.filter(Q(item_name__icontains=query))
            results = [{'id': item.sku, 'name': item.item_name, "url": reverse("item_detail", args=[item.sku])} for item
                       in items]

        return JsonResponse(results, safe=False)
    
@csrf_exempt
def stripe_config(request):
    if request.method == 'GET':
        stripe_config = {'publicKey': settings.STRIPE_PUBLISHABLE_KEY}
        return JsonResponse(stripe_config, safe=False)
def cancelled(request):
    return render(request, "payment_failed.html")
def success(request):
    if not request.user.is_authenticated:
        messages.success(request,"Your account has been created! please change your password. your password is same as your email")
    messages.success(request, "payment receipt has been sent to you on your email, please check!")
    return render(request, "payment_success.html")


# Site related views
def login(request: HttpRequest):
    if request.method == 'POST':
        email = request.POST.get("email")
        password = request.POST.get("passw")
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login_dj(request, user)
            messages.success(request, 'Login successful')
            return redirect("my_orders")
        else:
            messages.error(request, 'Invalid credentials')
            return render(request, "login.html", {"entered_email": email})

    if request.method == "GET":
        return render(request, "login.html")

def making_videos(request):
    videos = OurMakingVideos.objects.all()
    return render(request, "makingvideos.html", {"videos": videos})

def home(request: HttpRequest):
    front_medias = FrontMedia.objects.all()
    all_items = Item.objects.all()[:8]
    partners = Partners.objects.all()[::-1]
    best_sellings = BestSellingProducts.objects.all()
    items = []
    for best_selling in best_sellings:
        itm = Item.objects.get(sku=best_selling.item_sku)
        items.append(itm)

    return render(request, "home.html", {"partners": partners, 'best_selling_items': items,"all_items": all_items, "front_media": front_medias, "slider_image_count": front_medias.count()})


@login_required
def my_orders(request):
    my_orders_list = []
    if request.user.is_authenticated:
        my_orders_list = request.user.my_orders.all().order_by("-order_date")
        try:
            offset_minutes = request.session["user_timezone"]
            offset = timedelta(minutes=int(offset_minutes))
        except KeyError:
            offset = timedelta(minutes=0)

        for order in my_orders_list:
            order.order.date_created -= offset

    return render(request, "myorders.html", {"my_orders_list": my_orders_list})

@login_required
def profile(request: HttpRequest):
    user_details = {}
    user = request.user
    user_details["email"] = user.email

    user_details["first_name"] = user.first_name
    user_details["last_name"] = user.last_name

    return render(request, "profile.html", {"user_profile": user_details})

@login_required
def edit_profile(request: HttpRequest):
    user = request.user
    if request.method == 'GET':
        return render(request, "edit_profile.html", {"user": user})
    if request.method == 'POST':
        oldpass = request.POST.get("oldpass")
        newpass1 = request.POST.get("newpass1")
        newpass2 = request.POST.get("newpass2")
        email = request.POST.get("email")
        fname = request.POST.get("fname")
        lname = request.POST.get("lname")

        if oldpass and newpass1 and newpass2:
            if is_password_correct(request, oldpass):
                if newpass1 != newpass2:
                    messages.error(request, "New password doesn't match the re-typed password!")
                    return redirect("edit_profile")
                else:  # finally every thing is good
                    user.set_password(newpass1)
                    user.save()
                    update_session_auth_hash(request, user)
                    messages.success(request, "Password changed successfully!")
                    return redirect("profile")
            else:
                messages.error(request, "Old password Incorrect!")
                return redirect("edit_profile")

        update_instance(request.user, username=email, email=email, first_name=fname, last_name=lname)
        messages.success(request, "Profile updated successfully!")
        return redirect("profile")

def remove_from_cart(request: HttpRequest, cart_item_id):
    if request.method == 'GET':
        cart_item = get_object_or_404(CartItem, id=cart_item_id)
        cart_item.delete()
        return redirect("cart")

def cart(request: HttpRequest):
    if request.method == 'POST':
        item_sku = request.POST.get("item_sku")
        quantity = request.POST.get("quantity")
        price_id = request.POST.get("price_id")
        item = get_object_or_404(Item, sku=item_sku)
        if not item.weight:
            messages.error(request, f"Product dimentions not set!")
            return redirect('item_detail', item_sku=item_sku)
        if item.quantity < int(quantity):
            messages.error(request, f"maximum stock available {item.quantity}")
            return redirect('item_detail', item_sku=item_sku)

        request.session.save()
        session_key = request.session.session_key
        if request.user.is_authenticated:
            try:
                cart = Cart.objects.get(user=request.user)
            except Cart.DoesNotExist:
                cart = Cart.objects.create(user=request.user)
            if cart:
                cart.session_key = session_key
                cart.save()
        else:
            cart, _ = Cart.objects.get_or_create(session_key=session_key)
        
        cart_item = CartItem.objects.create(cart=cart, quantity=quantity, item_sku=item_sku)
        cart_item.item_name = item.item_name
        if item.main_image:
            cart_item.item_image_link=item.main_image.url
        else:
            cart_item.item_image_link= " "
        cart_item.item_category = item.category.category_name
        cart_item.item_product_type = item.product_type.product_type_name
        item_desc = item.description

        if len(item_desc) > 300:
            item_desc = item_desc[:300]

        if price_id:
            attr = get_object_or_404(Attributes, pk=price_id)
            cart_item.item_price = attr.price
            cart_item.variant = attr.value
            cart_item.item_name += f" | {attr.value}"
        else:
            cart_item.item_price = item.default_price

        cart_item.item_description = item_desc
        cart_item.save()
        messages.success(request, f"Product added to cart!")

        return redirect('cart')

    if request.method == 'GET':
        if request.user.is_authenticated:
            try:
                cart = Cart.objects.get(user=request.user)
            except Cart.DoesNotExist:
                cart = None
        else:
            session_key = request.session.session_key
            try:
                cart = Cart.objects.get(session_key=session_key)
            except Cart.DoesNotExist:   
                cart = None
        if cart:
            cart_items = cart.cart_items.all()
            total_items = cart_items.count()
            total_amount = sum(cart_item.calculate_total_price() for cart_item in cart_items)
        else: 
            cart_items = CartItem.objects.none()
            total_items = 0
            total_amount = 0
        if request.user.is_authenticated and cart:
            cart.user = request.user

        return render(request, "cart.html", {"cart_items": cart_items, "total_amount": total_amount,
                                             "total_items": total_items})

def product(request: HttpRequest, category_slug):
    selected_category = Category.objects.get(category_slug=category_slug)
    pid = request.GET.get("pid")
    sort_filter = request.GET.get("sort")
    price_filter_applied = False
    try:
        prmin, prmax = int(request.GET.get("prmin")), int(request.GET.get("prmax"))
        price_filter_applied = True
    except TypeError:
        prmin, prmax = None, None
    items = selected_category.category_items.all()
    max_money = items.aggregate(Max('default_price'))['default_price__max'] or 0
    max_money += 5
    product_types = ProductType.objects.filter(item__in=items).distinct()

    if pid:
        items = items.filter(product_type_id=pid)
    else:
        items = items.all()
    if prmin or prmax:
        items = items.filter(default_price__range=(prmin, prmax))

    desc = selected_category.description
    cat_desc_short = None
    cat_desc_long = None
    if desc:
        if len(desc) > 250:
            cat_desc_short = desc[:250]
            cat_desc_long = desc
        else:
            cat_desc_short = desc
            cat_desc_long = desc
    if sort_filter in ("bs", "plh", "phl", "dno", "don"):
        if sort_filter == 'bs':
            items = items.annotate(num_reviews=Count('review')).order_by('-num_reviews')
        elif sort_filter == 'plh':
            items = items.order_by('default_price')
        elif sort_filter == 'phl':
            items = items.order_by('-default_price')
        elif sort_filter == 'dno':
            items = items.order_by('-item_upload_date')
        elif sort_filter == 'don':
            items = items.order_by('item_upload_date')

    context = {
        "price_filter_applied": price_filter_applied,
        "prices_filters": [[i, i + 10] for i in range(0, int(max_money), 40)],
        "all_items": items,
        "product_types": product_types,
        "category": selected_category,
        "cat_desc_short": cat_desc_short,
        "cat_desc_long": cat_desc_long,
    }
    return render(request, "products.html", context)

def contact_us(request: HttpRequest):
    return render(request, "contact.html")

def about_us(request: HttpRequest):
    return render(request, "about.html")

def return_policy(request: HttpRequest):
    return render(request, "return_policy.html")

def logout_view(request: HttpRequest):
    logout(request)
    messages.success(request, "you have logged out successfully.")
    return redirect('home')

def register(request: HttpRequest):
    if request.method == 'GET':
        return render(request, "register.html")

    elif request.method == 'POST':
        uname = request.POST.get("uname")
        email = request.POST.get("email")
        password = request.POST.get("password")
        if User.objects.filter(username=email).exists():
            messages.error(request, f'email "{email}" already exists!')
            return redirect("register")

        User.objects.create_user(username=email, email=email, password=password,
                                 first_name=uname)
        messages.info(request, "Thanks for registering. You are now logged in.")
        user = authenticate(username=email, password=password)
        login_dj(request, user)

        return redirect("cart")

def item_detail(request, item_sku):
    current_item = get_object_or_404(Item, sku=item_sku)
    next_item = Item.objects.filter(sku__gt=current_item.sku).order_by('sku').first()
    previous_item = Item.objects.filter(sku__lt=current_item.sku).order_by('-sku').first()

    if not previous_item:
        previous_item = Item.objects.order_by('-sku').first()
    if not next_item:
        next_item = Item.objects.order_by('sku').first()

    selected_attribute_id = request.GET.get("selected_attribute")

    total_reviews, average_rating, all_reviews = current_item.get_rating_data()
    item_price = current_item.default_price
    attribute_list = current_item.attributes_set.all()
    if attribute_list:
        if selected_attribute_id:
            attr_obj = get_object_or_404(Attributes, pk=selected_attribute_id)
            item_price = attr_obj.price
        else:
            selected_attribute_id = attribute_list.first().id
    else:
        selected_attribute_id = 0
        
    item_showcases = []
    if current_item.video:
        item_showcases.append({"type": "video", "url": current_item.video.url, "ctr": 1})
    all_images = current_item.image_set.all()
    if all_images:
        for i, img in enumerate(all_images):
            ctr = i + 1
            if current_item.video:
                ctr += 1
            item_showcases.append({"type": "image", "url": img.image.url, "ctr": ctr})

    context = {
        "item_showcases": item_showcases,
        "pre_selected": int(selected_attribute_id),
        "attribute_list": attribute_list,
        "item_price": item_price,
        "item": current_item,
        "total_reviews": total_reviews,
        "average_rating": average_rating,
        "all_reviews": all_reviews,
        "next_item": next_item,
        "previous_item": previous_item,
    }

    return render(request, "item.html", context)

def create_review(request, item_id):
    item = get_object_or_404(Item, pk=item_id)
    if request.method == 'POST':
        rating = int(request.POST.get("rating"))
        comment = request.POST.get("reviewComment")
        try:
            Review.objects.create(user=request.user, item=item, review_star=rating, review_comment=comment)
            return redirect('item_detail', item_sku=item_id)

        except Exception as e:
            return HttpResponse(e)

def all_products(request):
    product_types = ProductType.objects.all()
    all_items = Item.objects.all()
    pid = request.GET.get("pid")
    sort_filter = request.GET.get("sort")
    try:
        prmin, prmax = int(request.GET.get("prmin")), int(request.GET.get("prmax"))
    except TypeError:
        prmin, prmax = None, None
    max_money = all_items.aggregate(Max('default_price'))['default_price__max'] or 0
    max_money += 5
    if pid:
        all_items = all_items.filter(product_type_id=pid)
    if prmin or prmax:
        all_items = all_items.filter(default_price__range=(prmin, prmax))
    if sort_filter in ("bs", "plh", "phl", "dno", "don"):
        if sort_filter == 'bs':
            all_items = all_items.annotate(num_reviews=Count('review')).order_by('-num_reviews')
        elif sort_filter == 'plh':
            all_items = all_items.order_by('default_price')
        elif sort_filter == 'phl':
            all_items = all_items.order_by('-default_price')
        elif sort_filter == 'dno':
            all_items = all_items.order_by('-item_upload_date')
        elif sort_filter == 'don':
            all_items = all_items.order_by('item_upload_date')

    context = {"product_types": product_types, "all_items": all_items,
               "prices_filters": [[i, i + 10] for i in range(0, int(max_money), 10)]}
    return render(request, "all_products.html", context)

def is_superuser(user):
    return user.is_superuser

@staff_member_required
def admin_orders(request):
    admin_orders = Order.objects.all().order_by("-date_created")
    try:
        offset_minutes = request.session["user_timezone"]
        offset = timedelta(minutes=int(offset_minutes))
    except KeyError:
        offset = timedelta(minutes=0)

    for order in admin_orders:
        order.date_created -= offset
    return render(request, "orders.html", {"orders": admin_orders})
