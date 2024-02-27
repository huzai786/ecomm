from django.db import models
from ckeditor.fields import RichTextField
from django_resized import ResizedImageField
import uuid
from django.urls import reverse
from django.contrib.auth import get_user_model


class Category(models.Model):
    category_name = models.CharField("Category Name", max_length=300, null=False)
    short_description = models.TextField("Short description", max_length=1000, null=False)
    image = models.ImageField(upload_to='static/images/', null=True, blank=True)
    category_slug = models.SlugField(null=False)
    description = RichTextField(null=True, blank=True)


    def __str__(self):
        return f"{self.category_name}"

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'

class ProductType(models.Model):
    product_type_name = models.CharField("product type name", max_length=200, blank=False, null=False)
    product_type_slug = models.SlugField(null=True, blank=True)
    def __str__(self):
        return f"{self.product_type_name}"

    class Meta:
        verbose_name = 'Product Type'
        verbose_name_plural = 'Product Types'

class Item(models.Model):
    item_name = models.CharField("item name", max_length=300, blank=False, null=False)
    product_type = models.ForeignKey(ProductType, null=False, blank=False, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(null=False, default=0)
    category = models.ForeignKey(Category, null=False, blank=False, on_delete=models.CASCADE, related_name="category_items")
    description = RichTextField()
    item_specification = RichTextField(blank=True, null=True)
    sold_out = models.BooleanField(default=False, null=True, editable=False)
    default_price = models.DecimalField(null=False, blank=False, decimal_places=2, max_digits=5)
    sku = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, null=False, primary_key=True)

    main_image = ResizedImageField(size=[190, 200], upload_to="static/images/product_main_image", null=True, blank=True)
    video = models.FileField(upload_to="static/videos/", null=True, blank=True)
    item_upload_date = models.DateTimeField(auto_created=True, auto_now_add=True)
    attribute_list_name = models.CharField(max_length=200, null=True, blank=True)

    height = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)  # inches
    length = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)  # inches
    width = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)  # inches
    weight = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)  # in ounces

    def get_absolute_url(self):
        return reverse('item_detail', kwargs={"item_sku": str(self.sku)})

    def get_rating_data(self):
        reviews = self.review_set.all().order_by('-upload_date')
        if reviews:
            return self.get_rating_count(reviews), self.get_average_rating(reviews), reviews
        return None, None, None

    def get_star_code(self):
        html = ""
        avg_rating = self.get_average_rating()
        for i in range(1, 6):
            if i <= avg_rating:
                html += "<span class='fa fa-star checked'></span>"
            else:
                html += "<span class='fa fa-star'></span>"
        return html

    def get_average_rating(self, reviews=None):
        if not reviews:
            reviews = self.review_set.all()
        if reviews:
            return sum([r.review_star for r in reviews]) / len(reviews)
        return 0

    def get_rating_count(self, reviews=None):
        if not reviews:
            reviews = self.review_set.all()
        return len(reviews)

    def __str__(self):
        return f"{self.item_name}"

    class Meta:
        verbose_name = 'Item'
        verbose_name_plural = 'Items'

class Attributes(models.Model):
    value = models.CharField(max_length=50)
    price = models.DecimalField(null=False, blank=False, decimal_places=2, max_digits=5)
    parent = models.ForeignKey(Item, on_delete=models.CASCADE, null=False)

class Image(models.Model):
    image = models.ImageField(upload_to="static/images/product_images", null=True, blank=True)
    parent = models.ForeignKey(Item, on_delete=models.CASCADE)

# Item detail related stuff ended here.

class Review(models.Model):
    review_star = models.DecimalField(default=0, max_digits=2, decimal_places=1)
    review_comment = models.TextField(null=True, blank=True)
    item = models.ForeignKey(Item, on_delete=models.CASCADE, null=False)
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, null=False)
    upload_date = models.DateTimeField(auto_created=True, auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - stars: {self.review_star}"

# cart and orders models

class UserDetails(models.Model):
    user = models.OneToOneField(get_user_model(), on_delete=models.CASCADE, null=False)
    address_object_id = models.CharField(max_length=100, null=False)
    phone = models.CharField(max_length=20, null=True)
    country = models.CharField(max_length=20, null=True)
    addr_line1 = models.CharField(max_length=300, null=True)
    addr_line2 = models.CharField(max_length=300, null=True)
    postal_code = models.CharField(max_length=40, null=True)
    city = models.CharField(max_length=100, null=True)
    state = models.CharField(max_length=100, null=True)
    name = models.CharField(max_length=100, null=True)

    def __str__(self):
        return f"{self.name} - {self.phone}"
    
    class Meta:
        verbose_name = 'User Detail'
        verbose_name_plural = 'User Details'

class Cart(models.Model):
    user = models.OneToOneField(get_user_model(), on_delete=models.CASCADE, related_name="cart", null=True, blank=True, unique=True)
    session_key = models.CharField(max_length=40, unique=False)

    class Meta:
        verbose_name = 'Customer Cart'
        verbose_name_plural = 'Customer Cart'

    def get_total_amount(self):
        amnt = 0
        for cart_item in self.cart_items.all():
            amnt += float(cart_item.calculate_total_price())
        return amnt
    
    def get_parcel_size(self): 
        """change this in future to calculate the parcel box, current it just returns first cart
        items dimentions"""
        cis = self.cart_items.first()
        if cis:
            item = Item.objects.get(sku=cis.item_sku)
            p = {
                "length": str(item.length),
                "width": str(item.width),
                "height": str(item.height),
                "distance_unit": "in",
                "weight": str(item.weight),
                "mass_unit": "lb"
            }
            return p
        

    def __str__(self):
        return f"{self.session_key}"
    
class CartItem(models.Model):
    cart = models.ForeignKey('Cart', null=False, on_delete=models.CASCADE, related_name="cart_items")
    
    # item details, its variant, its price and its quantity 
    item_name = models.CharField(max_length=300)
    item_category = models.CharField(max_length=300)
    item_product_type = models.CharField(max_length=300)
    item_sku = models.CharField(max_length=200)
    item_image_link = models.CharField(max_length=300)
    item_description = models.CharField(max_length=300)
    quantity = models.PositiveIntegerField(default=1)
    variant = models.CharField(max_length=50, null=True, blank=True)
    item_price = models.DecimalField(null=True, blank=False, decimal_places=2, max_digits=5)
    date_added = models.DateTimeField(auto_created=True, auto_now_add=True)

    def __str__(self):
        return f"{self.item_name} x {self.quantity}"

    def calculate_total_price(self) -> int:
        """returns items total price total in dollor, and in decimal"""
        return self.item_price * self.quantity

    def individual_price(self):
        """return individual price in cents"""
        return int(self.item_price * 100)

    class Meta:
        verbose_name = 'Customer Cart Item'
        verbose_name_plural = 'Customer Cart Items'

class MyOrders(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name="my_orders")
    order = models.ForeignKey("Order", on_delete=models.CASCADE)
    order_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email}: {self.order.order_id}"

    class Meta:
        verbose_name = 'My Order'
        verbose_name_plural = 'My Orders'

class Order(models.Model):
    STATUS = [
        ("PENDING", "PENDING"),
        ("DELIVERED", "DELIVERED")
    ]
    PAYMENT_STATUS = [
        ("PENDING", "PENDING"),
        ("PAID", "PAID")
    ]
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    order_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, null=False, primary_key=True)
    email = models.EmailField()
    contact_name = models.CharField(max_length=60)
    goshippo_address_id = models.CharField(max_length=100)
    total_amount = models.CharField(max_length=50)
    shipping_fee = models.CharField(max_length=50)
    payment_status = models.CharField(max_length=50, choices=PAYMENT_STATUS, default="PAID")
    label_url = models.CharField(max_length=500, null=True)
    tracking_url_provider = models.CharField(max_length=500, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, null=False, blank=False, choices=STATUS, default="PENDING")

    def __str__(self):
        return f"Order #{self.order_id} - {self.email}"

    class Meta:
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'

class OrderItem(models.Model):
    item_name = models.CharField(max_length=255)
    item_price = models.DecimalField(max_digits=10, decimal_places=2)
    variant = models.CharField(max_length=255, null=True, blank=True)
    category = models.CharField(max_length=50)
    product_type = models.CharField(max_length=50)
    item_quantity = models.PositiveIntegerField()
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="order_items")

    def __str__(self):
        return f"Order #{self.order.order_id} - {self.item_name}"

    class Meta:
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'
