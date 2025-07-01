from rest_framework import serializers
from .models import Product, Category, Order

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']

class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    average_rating = serializers.FloatField(read_only=True)
    class Meta:
        model = Product
        fields = ['id', 'name', 'price', 'category', 'description', 'image', 'average_rating']

class OrderSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    class Meta:
        model = Order
        fields = ['id', 'product', 'quantity', 'price', 'address', 'phone', 'date', 'status'] 