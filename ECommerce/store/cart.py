class Cart:
    def __init__(self, session):
        self.session = session
        self.cart = session.get('cart', {})

    def add(self, product_id):
        product_id = str(product_id)
        if product_id in self.cart:
            self.cart[product_id] += 1
        else:
            self.cart[product_id] = 1
        self.save()

    def remove(self, product_id):
        product_id = str(product_id)
        if product_id in self.cart:
            if self.cart[product_id] <= 1:
                self.cart.pop(product_id)
            else:
                self.cart[product_id] -= 1
        self.save()

    def save(self):
        self.session['cart'] = self.cart
        self.session.modified = True

    def clear(self):
        self.cart = {}
        self.save()

    def get_items(self):
        return self.cart 