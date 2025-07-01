from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.contrib.auth.hashers import make_password
from django.contrib.auth.hashers import  check_password
from .models import *
from django.views import  View
from .cart import Cart as CartHelper
from .forms import SignupForm, LoginForm, CustomerProfileForm, ReviewForm
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.utils.decorators import method_decorator
from rest_framework import generics, permissions
from .serializers import ProductSerializer, CategorySerializer, OrderSerializer
from django.contrib.auth.views import PasswordResetView
from django.core.cache import cache

class Index(View):

    def post(self , request):
        product = request.POST.get('product')
        remove = request.POST.get('remove')
        cart = CartHelper(request.session)
        if remove:
            cart.remove(product)
        else:
            cart.add(product)
        print('cart' , cart.get_items())
        return redirect('homepage')



    def get(self , request):
        # print()
        return HttpResponseRedirect(f'/store{request.get_full_path()[1:]}')

def store(request):
    cart = request.session.get('cart')
    if not cart:
        request.session['cart'] = {}
    # Cache categories
    categories = cache.get('categories')
    if not categories:
        categories = Category.get_all_categories()
        cache.set('categories', categories, 60 * 10)  # Cache for 10 minutes
    categoryID = request.GET.get('category')
    search_query = request.GET.get('search', '').strip()
    page_number = request.GET.get('page', 1)
    # Cache product list by category and search
    cache_key = f'products_{categoryID}_{search_query}'
    products = cache.get(cache_key)
    if not products:
        if categoryID:
            products = Product.objects.select_related('category').filter(category=categoryID)
        else:
            products = Product.objects.select_related('category').all()
        if search_query:
            products = products.filter(name__icontains=search_query)
        cache.set(cache_key, products, 60 * 5)  # Cache for 5 minutes
    # Pagination
    paginator = Paginator(products, 6)  # 6 products per page
    page_obj = paginator.get_page(page_number)
    data = {
        'products': page_obj.object_list,
        'categories': categories,
        'search_query': search_query,
        'selected_category': categoryID,
        'page_obj': page_obj
    }
    print('you are : ', request.session.get('email'))
    return render(request, 'index.html', data)


class Cart(View):
    def get(self, request):
        cart = CartHelper(request.session)
        items = cart.get_items()
        coupon_code = request.GET.get('coupon') or request.session.get('coupon_code')
        coupon = None
        discount = 0
        total = 0
        if items:
            ids = list(items.keys())
            products = Product.get_products_by_id(ids)
            if coupon_code:
                from .models import Coupon
                try:
                    coupon = Coupon.objects.get(code__iexact=coupon_code, active=True)
                    request.session['coupon_code'] = coupon_code
                except Coupon.DoesNotExist:
                    coupon = None
                    request.session['coupon_code'] = ''
            total, discount = cart_total_with_coupon(products, items, coupon)
            return render(request, 'cart.html', {'products': products, 'coupon': coupon, 'discount': discount, 'total': total})
        else:
            return render(request, 'cart.html', {'products': [], 'coupon': None, 'discount': 0, 'total': 0})



class CheckOut(View):
    def post(self, request):
        address = request.POST.get('address')
        phone = request.POST.get('phone')
        customer = request.session.get('customer')
        cart = CartHelper(request.session)
        items = cart.get_items()
        products = Product.get_products_by_id(list(items.keys()))
        coupon_code = request.session.get('coupon_code')
        coupon = None
        if coupon_code:
            from .models import Coupon
            try:
                coupon = Coupon.objects.get(code__iexact=coupon_code, active=True)
            except Coupon.DoesNotExist:
                coupon = None
        total, discount = cart_total_with_coupon(products, items, coupon)
        print(address, phone, customer, items, products, coupon, discount, total)
        for product in products:
            order = Order(customer=Customer(id=customer),
                          product=product,
                          price=product.price,
                          address=address,
                          phone=phone,
                          quantity=items.get(str(product.id)))
            order.save()
        cart.clear()
        request.session['coupon_code'] = ''
        messages.success(request, f'Order placed successfully! Discount applied: {discount}')
        return redirect('cart')
    
class Login(View):
    return_url = None
    def get(self , request):
        Login.return_url = request.GET.get('return_url')
        form = LoginForm()
        return render(request , 'login.html', {'form': form})

    def post(self , request):
        form = LoginForm(request.POST)
        error_message = None
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            customer = Customer.get_customer_by_email(email)
            print(customer)
            if customer:
                flag = check_password(password, customer.password)
                if flag:
                    request.session['customer'] = customer.id
                    messages.success(request, 'Login successful!')
                    if Login.return_url:
                        return HttpResponseRedirect(Login.return_url)
                    else:
                        Login.return_url = None
                        return redirect('homepage')
                else:
                    error_message = 'Email or Password invalid !!'
            else:
                error_message = 'Email or Password invalid !!'
        else:
            error_message = 'Invalid form input.'
        return render(request, 'login.html', {'form': form, 'error': error_message})

def logout(request):
    request.session.clear()
    return redirect('login')

class OrderView(View):


    def get(self , request ):
        customer = request.session.get('customer')
        orders = Order.objects.select_related('product').filter(customer=customer).order_by('-date')
        print(orders)
        return render(request , 'orders.html'  , {'orders' : orders})

class Signup(View):
    def get(self, request):
        form = SignupForm()
        return render(request, 'signup.html', {'form': form})

    def post(self, request):
        form = SignupForm(request.POST)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.password = make_password(form.cleaned_data['password'])
            customer.register()
            messages.success(request, 'Account created successfully! Please log in.')
            return redirect('login')
        else:
            return render(request, 'signup.html', {'form': form})

    def validateCustomer(self, customer):
        error_message = None;
        if (not customer.first_name):
            error_message = "First Name Required !!"
        elif len(customer.first_name) < 4:
            error_message = 'First Name must be 4 char long or more'
        elif not customer.last_name:
            error_message = 'Last Name Required'
        elif len(customer.last_name) < 4:
            error_message = 'Last Name must be 4 char long or more'
        elif not customer.phone:
            error_message = 'Phone Number required'
        elif len(customer.phone) < 10:
            error_message = 'Phone Number must be 10 char Long'
        elif len(customer.password) < 6:
            error_message = 'Password must be 6 char long'
        elif len(customer.email) < 5:
            error_message = 'Email must be 5 char long'
        elif customer.isExists():
            error_message = 'Email Address Already Registered..'
        # saving

        return error_message

class ProfileView(View):
    def get(self, request):
        customer_id = request.session.get('customer')
        if not customer_id:
            return redirect('login')
        customer = Customer.objects.get(id=customer_id)
        form = CustomerProfileForm(instance=customer)
        orders = Order.get_orders_by_customer(customer_id)
        return render(request, 'profile.html', {'form': form, 'orders': orders})

    def post(self, request):
        customer_id = request.session.get('customer')
        if not customer_id:
            return redirect('login')
        customer = Customer.objects.get(id=customer_id)
        form = CustomerProfileForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
        orders = Order.get_orders_by_customer(customer_id)
        return render(request, 'profile.html', {'form': form, 'orders': orders})

class WishlistView(View):
    def get(self, request):
        customer_id = request.session.get('customer')
        if not customer_id:
            return redirect('login')
        wishlist_items = Wishlist.objects.filter(customer_id=customer_id).select_related('product')
        return render(request, 'wishlist.html', {'wishlist_items': wishlist_items})

def add_to_wishlist(request, product_id):
    customer_id = request.session.get('customer')
    if not customer_id:
        return JsonResponse({'success': False, 'message': 'Login required.'})
    Wishlist.objects.get_or_create(customer_id=customer_id, product_id=product_id)
    return JsonResponse({'success': True, 'message': 'Added to wishlist.'})

def remove_from_wishlist(request, product_id):
    customer_id = request.session.get('customer')
    if not customer_id:
        return JsonResponse({'success': False, 'message': 'Login required.'})
    Wishlist.objects.filter(customer_id=customer_id, product_id=product_id).delete()
    return JsonResponse({'success': True, 'message': 'Removed from wishlist.'})

class ProductDetailView(View):
    def get(self, request, product_id):
        product = Product.objects.get(id=product_id)
        reviews = product.reviews.select_related('customer').order_by('-created_at')
        form = ReviewForm()
        avg_rating = product.average_rating()
        # Related products: same category, exclude current
        related_products = Product.objects.filter(category=product.category).exclude(id=product.id)[:4]
        return render(request, 'product_detail.html', {
            'product': product,
            'reviews': reviews,
            'form': form,
            'avg_rating': avg_rating,
            'related_products': related_products
        })

    def post(self, request, product_id):
        if not request.session.get('customer'):
            return redirect('login')
        product = Product.objects.get(id=product_id)
        customer = Customer.objects.get(id=request.session['customer'])
        form = ReviewForm(request.POST)
        if form.is_valid():
            review_obj, created = Review.objects.update_or_create(
                product=product, customer=customer,
                defaults={
                    'rating': form.cleaned_data['rating'],
                    'review': form.cleaned_data['review']
                }
            )
            messages.success(request, 'Review submitted!')
            return redirect('product_detail', product_id=product.id)
        reviews = product.reviews.select_related('customer').order_by('-created_at')
        avg_rating = product.average_rating()
        related_products = Product.objects.filter(category=product.category).exclude(id=product.id)[:4]
        return render(request, 'product_detail.html', {
            'product': product,
            'reviews': reviews,
            'form': form,
            'avg_rating': avg_rating,
            'related_products': related_products
        })
    
class OrderStatusUpdateView(View):
    @method_decorator(user_passes_test(lambda u: u.is_superuser))
    def post(self, request, order_id):
        status = request.POST.get('status')
        order = Order.objects.get(id=order_id)
        if status in ['Pending', 'Shipped', 'Delivered', 'Cancelled']:
            order.status = status
            order.save()
            messages.success(request, f'Order status updated to {status}!')
        return redirect('orders_admin')

class OrdersAdminView(View):
    @method_decorator(user_passes_test(lambda u: u.is_superuser))
    def get(self, request):
        orders = Order.objects.select_related('customer', 'product').all().order_by('-date')
        return render(request, 'orders_admin.html', {'orders': orders, 'status_choices': ['Pending', 'Shipped', 'Delivered', 'Cancelled']})

class ProductListAPI(generics.ListAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

class CategoryListAPI(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class OrderListAPI(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user_id = self.request.session.get('customer')
        return Order.objects.filter(customer_id=user_id)

class DebugPasswordResetView(PasswordResetView):
    def form_valid(self, form):
        print("Password reset requested for:", form.cleaned_data["email"])
        return super().form_valid(form)
    
def cart_total_with_coupon(products, cart, coupon):
    total = sum([product.price * cart.get(str(product.id), 0) for product in products])
    discount = 0
    if coupon:
        if coupon.discount_type == 'amount':
            discount = float(coupon.discount_value)
        elif coupon.discount_type == 'percent':
            discount = total * float(coupon.discount_value) / 100
    return max(total - discount, 0), discount
    
