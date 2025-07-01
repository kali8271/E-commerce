from django.test import TestCase, Client
from .models import Product, Category

# Create your tests here.

class StoreViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name='Fruits')
        self.product = Product.objects.create(name='Apple', price=10, category=self.category)

    def test_homepage_loads(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'E-Shop')

    def test_product_detail_loads(self):
        response = self.client.get(f'/product/{self.product.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Apple')

    def test_product_creation(self):
        product = Product.objects.create(name='Banana', price=5, category=self.category)
        self.assertEqual(product.name, 'Banana')
        self.assertEqual(product.price, 5)
        self.assertEqual(product.category, self.category)
