from django.contrib import admin
from .models import Category, Product, Customer, Order, Wishlist, Review, Coupon, UserActivity, Brand, Tag, OrderRequest, ProductQuestion



class AdminProduct(admin.ModelAdmin):
    list_display = ['name', 'price', 'category']



class AdminCategory(admin.ModelAdmin):
    list_display = ['name']


class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'brand', 'price', 'stock')
    list_filter = ('category', 'brand')
    search_fields = ('name',)


# Register your models here.
admin.site.register(Product, ProductAdmin)
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