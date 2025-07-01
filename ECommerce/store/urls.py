from django.contrib import admin
from django.urls import path
from .views import *
from .middlewares.auth import session_auth_required
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('', Index.as_view(), name='homepage'),
    path('store', store , name='store'),

    path('signup', Signup.as_view(), name='signup'),
    path('login', Login.as_view(), name='login'),
    path('logout', logout , name='logout'),
    path('cart', session_auth_required(Cart.as_view()), name='cart'),
    path('check-out', CheckOut.as_view() , name='checkout'),
    path('orders', session_auth_required(OrderView.as_view()), name='orders'),
    path('profile', session_auth_required(ProfileView.as_view()), name='profile'),
    path('wishlist', session_auth_required(WishlistView.as_view()), name='wishlist'),
    path('wishlist/add/<int:product_id>/', add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:product_id>/', remove_from_wishlist, name='remove_from_wishlist'),
    path('product/<int:product_id>/', ProductDetailView.as_view(), name='product_detail'),
    path('admin/orders/', OrdersAdminView.as_view(), name='orders_admin'),
    path('admin/orders/update/<int:order_id>/', OrderStatusUpdateView.as_view(), name='order_status_update'),
    path('password_reset/', DebugPasswordResetView.as_view(template_name='password_reset_form.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'), name='password_reset_complete'),
    path('api/products/', ProductListAPI.as_view(), name='api_products'),
    path('api/categories/', CategoryListAPI.as_view(), name='api_categories'),
    path('api/orders/', OrderListAPI.as_view(), name='api_orders'),
]