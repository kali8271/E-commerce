from django.contrib import admin
from .models import Category, Product, Customer, Order, Wishlist, Review, Coupon, UserActivity, Brand, Tag, OrderRequest, ProductQuestion



class AdminProduct(admin.ModelAdmin):
    list_display = ['name', 'price', 'category']



class AdminCategory(admin.ModelAdmin):
    list_display = ['name']


# Register your models here.
admin.site.register(Product, AdminProduct)
admin.site.register(Category , AdminCategory)
admin.site.register(Customer )
admin.site.register(Order )
admin.site.register(Wishlist)
admin.site.register(Review)
admin.site.register(Coupon)
admin.site.register(UserActivity)
admin.site.register(Brand)
admin.site.register(Tag)
admin.site.register(OrderRequest)
admin.site.register(ProductQuestion)