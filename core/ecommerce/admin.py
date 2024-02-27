from django.contrib import admin
from .models import (Category, ProductType, Item, Attributes, Cart, Image, Review, UserDetails, MyOrders, Order, CartItem)
from django.contrib.auth.models import Group


class AttributesInline(admin.TabularInline):
    model = Attributes
    extra = 1
class ImageInline(admin.StackedInline):
    model = Image
    extra = 1
class ItemAdmin(admin.ModelAdmin):
    inlines = [ImageInline, AttributesInline]
    list_filter = ["product_type"]

class OrderAdmin(admin.ModelAdmin):
    list_display = ("email", "date_created", "status")

admin.site.unregister(Group)
admin.site.register(Category)
admin.site.register(ProductType)
admin.site.register(Review)
admin.site.register(Item, ItemAdmin)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(UserDetails)


admin.site.register(MyOrders)
admin.site.register(Order, OrderAdmin)



