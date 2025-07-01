from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.contrib.auth.hashers import make_password
from django.contrib.auth.hashers import  check_password
from .models import *
from django.views import  View
from .cart import Cart as CartHelper
from .forms import SignupForm, LoginForm, CustomerProfileForm, ReviewForm, ProductQuestionForm
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.utils.decorators import method_decorator
from rest_framework import generics, permissions
from .serializers import ProductSerializer, CategorySerializer, OrderSerializer
from django.contrib.auth.views import PasswordResetView
from django.core.cache import cache
from rest_framework.permissions import IsAuthenticated
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
import calendar
from datetime import timedelta
import csv
from django.utils.encoding import smart_str
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.http import require_POST
from django.db.models import Count

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
    brands = Brand.objects.all()
    brand_id = request.GET.get('brand')
    categoryID = request.GET.get('category')
    search_query = request.GET.get('search', '').strip()
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    tag_id = request.GET.get('tag')
    page_number = request.GET.get('page', 1)
    # Cache product list by category and search
    cache_key = f'products_{categoryID}_{search_query}_{min_price}_{max_price}_{brand_id}_{tag_id}'
    products = cache.get(cache_key)
    if not products:
        if categoryID:
            products = Product.objects.select_related('category', 'brand').prefetch_related('tags').filter(category=categoryID)
        else:
            products = Product.objects.select_related('category', 'brand').prefetch_related('tags').all()
        if search_query:
            products = products.filter(name__icontains=search_query)
        if min_price:
            products = products.filter(price__gte=min_price)
        if max_price:
            products = products.filter(price__lte=max_price)
        if brand_id:
            products = products.filter(brand_id=brand_id)
        if tag_id:
            products = products.filter(tags__id=tag_id)
        cache.set(cache_key, products, 60 * 5)  # Cache for 5 minutes
    # Get recent reviews for testimonials
    testimonials = Review.objects.select_related('customer', 'product').order_by('-created_at')[:4]
    # Recently viewed products
    viewed_ids = request.session.get('recently_viewed', [])
    recently_viewed = Product.objects.filter(id__in=viewed_ids) if viewed_ids else []
    # Personalized recommendations
    recommended_products = []
    customer_id = request.session.get('customer')
    if customer_id:
        # Recommend products from categories the user ordered or viewed, excluding already ordered/viewed
        ordered_ids = Order.objects.filter(customer_id=customer_id).values_list('product_id', flat=True)
        ordered_categories = Product.objects.filter(id__in=ordered_ids).values_list('category_id', flat=True)
        viewed_categories = Product.objects.filter(id__in=viewed_ids).values_list('category_id', flat=True)
        categories_of_interest = set(list(ordered_categories) + list(viewed_categories))
        recommended_products = Product.objects.filter(category_id__in=categories_of_interest).exclude(id__in=list(ordered_ids) + viewed_ids)[:6]
        if not recommended_products:
            recommended_products = Product.objects.exclude(id__in=list(ordered_ids) + viewed_ids)[:6]
    else:
        # For guests, show popular products (by order count)
        recommended_products = Product.objects.annotate(order_count=Count('order')).order_by('-order_count')[:6]
    # Pagination
    paginator = Paginator(products, 6)  # 6 products per page
    page_obj = paginator.get_page(page_number)
    tags = Tag.objects.all()
    data = {
        'products': page_obj.object_list,
        'categories': categories,
        'brands': brands,
        'tags': tags,
        'search_query': search_query,
        'selected_category': categoryID,
        'selected_brand': brand_id,
        'selected_tag': tag_id,
        'min_price': min_price,
        'max_price': max_price,
        'page_obj': page_obj,
        'testimonials': testimonials,
        'recently_viewed': recently_viewed,
        'recommended_products': recommended_products
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
        order_ids = []
        for product in products:
            order = Order(customer=Customer(id=customer),
                          product=product,
                          price=product.price,
                          address=address,
                          phone=phone,
                          quantity=items.get(str(product.id)))
            order.save()
            order_ids.append(order.id)
        cart.clear()
        request.session['coupon_code'] = ''
        messages.success(request, f'Order placed successfully! Discount applied: {discount}')
        # Log activity
        if customer:
            user_obj = Customer.objects.get(id=customer)
            UserActivity.objects.create(user=user_obj, action='order', details=f'Order placed. Total: {total}, Discount: {discount}')
            # Send order confirmation email
            subject = 'Order Confirmation - E-Commerce Site'
            order_list = "\n".join([f"- {Product.objects.get(id=pid).name} (Qty: {items.get(str(pid), 1)})" for pid in items.keys()])
            message = f"Dear {user_obj.first_name},\n\nThank you for your order!\n\nOrder Details:\n{order_list}\n\nTotal: ₹{total}\nDiscount: ₹{discount}\n\nWe will notify you when your order is shipped.\n\nBest regards,\nE-Commerce Team"
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user_obj.email], fail_silently=True)
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
                    # Log activity
                    UserActivity.objects.create(user=customer, action='login', details='User logged in.')
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
            # Log activity
            UserActivity.objects.create(user=customer, action='signup', details='User signed up.')
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
        # Track recently viewed products
        viewed = request.session.get('recently_viewed', [])
        if product.id not in viewed:
            viewed = [product.id] + viewed
            viewed = viewed[:6]  # Keep only last 6
            request.session['recently_viewed'] = viewed
        reviews = product.reviews.select_related('customer').order_by('-created_at')
        form = ReviewForm()
        avg_rating = product.average_rating()
        # Related products: same category, exclude current
        related_products = Product.objects.filter(category=product.category).exclude(id=product.id)[:4]
        # Product Q&A
        question_form = ProductQuestionForm()
        answered_questions = product.questions.filter(status='answered')
        return render(request, 'product_detail.html', {
            'product': product,
            'reviews': reviews,
            'form': form,
            'avg_rating': avg_rating,
            'related_products': related_products,
            'question_form': question_form,
            'answered_questions': answered_questions
        })

    def post(self, request, product_id):
        if not request.session.get('customer'):
            return redirect('login')
        product = Product.objects.get(id=product_id)
        customer = Customer.objects.get(id=request.session['customer'])
        # Handle review form
        if 'review' in request.POST:
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
                # Log activity
                UserActivity.objects.create(user=customer, action='review', details=f'Reviewed product {product.name} with rating {form.cleaned_data["rating"]}')
                return redirect('product_detail', product_id=product.id)
        # Handle question form
        elif 'question' in request.POST:
            question_form = ProductQuestionForm(request.POST)
            if question_form.is_valid():
                ProductQuestion.objects.create(
                    product=product,
                    customer=customer,
                    question=question_form.cleaned_data['question']
                )
                messages.success(request, 'Your question has been submitted and is pending approval.')
                return redirect('product_detail', product_id=product.id)
        # Fallback: show page
        reviews = product.reviews.select_related('customer').order_by('-created_at')
        avg_rating = product.average_rating()
        related_products = Product.objects.filter(category=product.category).exclude(id=product.id)[:4]
        question_form = ProductQuestionForm()
        answered_questions = product.questions.filter(status='answered')
        return render(request, 'product_detail.html', {
            'product': product,
            'reviews': reviews,
            'form': ReviewForm(),
            'avg_rating': avg_rating,
            'related_products': related_products,
            'question_form': question_form,
            'answered_questions': answered_questions
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
            # Send status update email
            if order.customer and order.customer.email:
                subject = f'Order Status Update - {order.product.name}'
                message = f"Dear {order.customer.first_name},\n\nYour order for {order.product.name} is now: {status}.\n\nOrder ID: {order.id}\nProduct: {order.product.name}\nStatus: {status}\n\nThank you for shopping with us!\n\nBest regards,\nE-Commerce Team"
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [order.customer.email], fail_silently=True)
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
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            return Order.objects.filter(customer__email=user.email)
        return Order.objects.none()

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

def newsletter_signup(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        if email:
            obj, created = NewsletterSubscriber.objects.get_or_create(email=email)
            if created:
                messages.success(request, 'Thank you for subscribing!')
            else:
                messages.info(request, 'You are already subscribed.')
        return redirect(request.META.get('HTTP_REFERER', '/'))
    
def add_to_compare(request, product_id):
    compare = request.session.get('compare', [])
    if product_id not in compare:
        compare.append(product_id)
        request.session['compare'] = compare
    return redirect(request.META.get('HTTP_REFERER', '/'))

def remove_from_compare(request, product_id):
    compare = request.session.get('compare', [])
    if product_id in compare:
        compare.remove(product_id)
        request.session['compare'] = compare
    return redirect(request.META.get('HTTP_REFERER', '/'))

def compare_products(request):
    compare = request.session.get('compare', [])
    products = Product.objects.filter(id__in=compare)
    return render(request, 'compare.html', {'products': products})

@staff_member_required
def admin_analytics(request):
    from django.db.models import Sum, Count
    total_sales = Order.objects.aggregate(total=Sum('price'))['total'] or 0
    total_orders = Order.objects.count()
    total_users = Customer.objects.count()
    top_products = Product.objects.annotate(order_count=Count('order')).order_by('-order_count')[:5]
    recent_activity = UserActivity.objects.select_related('user').order_by('-timestamp')[:10]
    # Sales per month for last 12 months
    now = timezone.now()
    months = []
    sales = []
    for i in range(11, -1, -1):
        month = (now - timedelta(days=30*i)).replace(day=1)
        next_month = (month + timedelta(days=32)).replace(day=1)
        month_label = month.strftime('%b %Y')
        month_sales = Order.objects.filter(date__gte=month, date__lt=next_month).aggregate(total=Sum('price'))['total'] or 0
        months.append(month_label)
        sales.append(float(month_sales))
    return render(request, 'admin_analytics.html', {
        'total_sales': total_sales,
        'total_orders': total_orders,
        'total_users': total_users,
        'top_products': top_products,
        'recent_activity': recent_activity,
        'months': months,
        'sales': sales
    })
    
@staff_member_required
def export_orders_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=orders.csv'
    writer = csv.writer(response)
    writer.writerow(['Order ID', 'Customer', 'Product', 'Price', 'Date', 'Status'])
    for order in Order.objects.select_related('customer', 'product').all():
        writer.writerow([
            order.id,
            order.customer.email if order.customer else '',
            order.product.name if order.product else '',
            order.price,
            order.date.strftime('%Y-%m-%d %H:%M'),
            order.status
        ])
    return response
    
@require_POST
def request_order_action(request, order_id, action_type):
    customer_id = request.session.get('customer')
    if not customer_id:
        return redirect('login')
    order = Order.objects.get(id=order_id)
    reason = request.POST.get('reason', '')
    if action_type in ['cancellation', 'return']:
        OrderRequest.objects.create(
            order=order,
            customer_id=customer_id,
            request_type=action_type,
            reason=reason
        )
        messages.success(request, f'{action_type.title()} request submitted for Order #{order.id}.')
    return redirect('profile')
    
