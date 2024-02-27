import json
from django.contrib.auth.hashers import check_password
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime
import pytz


def is_password_correct(request, password_to_check):
    user = request.user
    return check_password(password_to_check, user.password)

def save_json(name, obj):
    with open(name, 'w') as f:
        json.dump(obj, f)

def update_instance(instance, **kwargs):
    for k, v in kwargs.items():
        setattr(instance, k, v)
    instance.save()

def get_timezone_by_country(country):
    country_timezones = {
        'United Kingdom': 'Europe/London',
        'United States': 'America/New_York',
        'Canada': 'America/Toronto',
    }
    return country_timezones.get(country, 'UTC')

def format_order_date(order_date, country):
    order_datetime = datetime.strptime(str(order_date), "%Y-%m-%d %H:%M:%S.%f%z")
    user_timezone = pytz.timezone(get_timezone_by_country(country))
    order_datetime_user_tz = order_datetime.astimezone(user_timezone)
    formatted_order_date = order_datetime_user_tz.strftime("%I:%M:%S %p %d %B %Y")
    return formatted_order_date


def sent_order_email(email, order, country):
    subject = "Your Order has been placed Successfully."

    # Build the message body
    message_body = f"Dear {order.contact_name},\n\n"
    message_body += f"Thank you for placing an order with Nida Tradings. Your order has been successfully placed and is currently being processed.\n\n"

    order_date = order.date_created
    order_string = format_order_date(order_date, country)

    admin_order_date = ""
    admin_order_date += "USA TIME: " + format_order_date(order_date, "United States") + "\n"

    # Include order details
    order_detail = f"Order ID: {order.order_id}\n"

    order_detail += f"Order Date ({country}): {order_string}\n\n"

    # Include customer details
    order_detail += f"Shipping Address:\n"
    order_detail += f"\t\tName: {order.contact_name}\n"
    order_detail += f"\t\tEmail: {order.email}\n"
    order_detail += f"\t\tCountry: {order.user.userdetails.country}\n"
    order_detail += f"\t\tCity: {order.user.userdetails.city}\n"
    order_detail += f"\t\tState: {order.user.userdetails.state}\n"
    order_detail += f"\t\tAddress Line 1: {order.user.userdetails.addr_line1}\n"
    order_detail += f"\t\tAddress Line 2: {order.user.userdetails.addr_line2}\n"
    order_detail += f"\t\tPostal Code: {order.user.userdetails.postal_code}\n"
    order_detail += f"\t\tPhone Number: {order.user.userdetails.phone}\n\n"

    # Include order items
    order_detail += "Ordered Items:\n"
    for i, item in enumerate(order.order_items.all()):
        order_detail += f"#{i+1}: {item.item_quantity} x {item.item_name} ({item.variant}) - ${item.item_price}\n"

    # Include order summary
    order_detail += f"\nOrder Summary:\n"
    order_detail += f"\t\ttotal Amount Paid: ${order.total_amount}\n"
    order_detail += f"\t\tShipping Fee: ${order.shipping_fee}\n"

    # Include payment status
    order_detail += f"\t\tPayment Status: {order.payment_status}\n\n"

    # Add a closing message
    message_body += order_detail
    message_body += "If you have any questions or concerns about your order, please contact us at +1 (612) 458-5827.\n\n"
    message_body += "Thank you for choosing Nida Tradings!\n"

    # Build the sender email address
    from_email = settings.DEFAULT_FROM_EMAIL

    # Send the email
    send_mail(subject, message_body, from_email, [email], fail_silently=True)
    admin_order_date += order_detail
    send_mail("An Order has Been Placed", admin_order_date, from_email, settings.ADMIN_EMAILS, fail_silently=True)
