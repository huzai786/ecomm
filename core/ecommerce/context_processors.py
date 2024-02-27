from .models import Cart, Category
from front_app_manager.models import TopSliderContent, Watsapp

def custom_context(request):
    all_categories = Category.objects.all()
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
        except Cart.DoesNotExist:
            cart = None
        if cart:
            cart_items = cart.cart_items.all()
        else:
            cart_items = []
    else:
        current_cart = Cart.objects.filter(session_key=request.session.session_key).first()
        if current_cart:
            cart_items = current_cart.cart_items.all()
        else:
            cart_items = []
    top_bar_items = TopSliderContent.objects.all()
    watsapp = Watsapp.objects.all().first()
    if watsapp:
        watsapp_cart = watsapp.cart_text
        watsapp_call = watsapp.call_text
    else:
        watsapp_cart = None
        watsapp_call = None

    return {
        "watsapp_cart": watsapp_cart,
        "watsapp_call": watsapp_call,
        "top_bar_items" : top_bar_items,
        "cart_items": cart_items,
        "cart_items_count": cart_items.count() if cart_items else 0,
        "all_categories": all_categories,
        "session_key": request.session.session_key,
    }

