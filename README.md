# E-Commerce Django Project

A modern, feature-rich e-commerce web application built with Django.

## Features
- User authentication (signup, login, password reset)
- Product catalog with categories, brands, tags, and advanced filtering
- Product detail pages with reviews, Q&A, and related products
- Shopping cart and wishlist (session-based)
- Order placement, order history, and profile management
- Coupon/discount system
- Newsletter signup (footer)
- Product comparison and recently viewed products
- Admin analytics dashboard (sales, top products, user activity, CSV export)
- REST API with JWT authentication
- Internationalization (i18n) and language switcher
- Redis caching for performance
- Product stock management
- Mock payment gateway integration (Stripe demo)
- PWA support (offline, add to home screen)
- Automated tests for key views and models

## Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd E-commerce/ECommerce
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Apply migrations:**
   ```bash
   python manage.py migrate
   ```

5. **Create a superuser (admin):**
   ```bash
   python manage.py createsuperuser
   ```

6. **Run the development server:**
   ```bash
   python manage.py runserver
   ```

7. **Access the site:**
   - Main site: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
   - Admin: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

## Usage
- Browse products, add to cart/wishlist, and place orders.
- Use the admin dashboard for analytics and product management.
- Test newsletter signup in the footer.
- Try the PWA features (add to home screen, offline support).
- Run tests with:
  ```bash
  python manage.py test store
  ```

## Notes
- For real payments, integrate with Stripe, Razorpay, or PayPal using their official SDKs.
- For production, configure proper email backend, static/media file hosting, and security settings.

---

**Enjoy your modern Django e-commerce platform!** 