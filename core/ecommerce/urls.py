from django.urls import path
from ecommerce import views

urlpatterns = [
    path('config/', views.stripe_config),
    path('webhook/', views.stripe_webhook),
    path("cancel/", views.cancelled, name='cancelled'),
    path("success/", views.success, name='success'),
    path('set_timezone/', views.set_timezone, name='set_timezone'),
    path('autocomplete/', views.autocomplete_view, name='autocomplete'),
    
    path("", views.home, name='home'),
    path("login/", views.login, name='login'),
    path("making_videos/", views.making_videos, name='making_videos'),
    path("cart/", views.cart, name='cart'),
    path("delete_cart_item/<int:cart_item_id>/", views.remove_from_cart, name='delete_cart_item'),
    path("profile/", views.profile, name='profile'),
    path("edit-profile/", views.edit_profile, name='edit_profile'),
    path("register/", views.register, name='register'),
    path("return_policy/", views.return_policy, name='return_policy'),
    path("category/<slug:category_slug>/", views.product, name='products'),
    path('create_review/<uuid:item_id>/', views.create_review, name='create_review'),
    path("all_products", views.all_products, name='all_products'),
    path("about_us/", views.about_us, name='about-us'),
    path("contact_us/", views.contact_us, name='contact-us'),
    path("item/<uuid:item_sku>/", views.item_detail, name='item_detail'),
    path("logout/", views.logout_view, name='logout'),

    path('my_orders/', views.my_orders, name='my_orders'),
    path('orders/', views.admin_orders, name='orders'),
    path('checkout/', views.checkout, name='checkout'),
    path('billing/', views.billing, name='billing'),

]
