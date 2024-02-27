from django.db import models

# Create your models here.
class FrontMedia(models.Model):
    mtypes = [
        ("image", "image"),
        ("video", "video"),
    ]
    media_type = models.CharField(max_length=50, choices=mtypes, null=False)
    image = models.ImageField(upload_to="static/images/frontEnd", null=True, blank=True)
    video = models.FileField(upload_to="static/videos/frontEnd", null=True, blank=True)


    def __str__(self):
        return f"image path: {self.image.path}"

    class Meta:
        app_label = 'front_app_manager'


class TopSliderContent(models.Model):
    text = models.CharField(max_length=300, null=False)
    link = models.CharField(max_length=300, null=False)

    def __str__(self):
        return f"text: {self.text}"

    class Meta:
        app_label = 'front_app_manager'


class Partners(models.Model):
    partner_image = models.ImageField(upload_to="static/images/partner_images", null=True, blank=True)
    partner_designation = models.CharField(max_length=300, null=False)
    partner_name = models.CharField(max_length=300, null=False)

    def __str__(self):
        return f"{self.partner_name} - {self.partner_designation}"

    class Meta:
        app_label = 'front_app_manager'
        verbose_name = 'Partners'
        verbose_name_plural = 'Partners'


class Watsapp(models.Model):
    cart_text = models.CharField(max_length=50)
    call_text = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.cart_text}"
    
    class Meta:
        app_label = 'front_app_manager'
        verbose_name = 'Watsapp Number'
        verbose_name_plural = 'Watsapp Number'

class BestSellingProducts(models.Model):
    item_sku = models.CharField(max_length=300)

    def __str__(self):
        return f"{self.item_sku}"
    
    class Meta:
        app_label = 'front_app_manager'
        verbose_name = 'Best Selling item list'
        verbose_name_plural = 'Best Selling item list'

class OurMakingVideos(models.Model):
    video = models.FileField(upload_to="static/videos/making_videos", null=True, blank=True)


    class Meta:
        app_label = 'front_app_manager'
        verbose_name = 'Our Making Videos'
        verbose_name_plural = 'Our Making Videos'
