# shop

Checkout logic shared by the website and the mobile app.

- Website: customers can enter a discount code on the cart page (the cart
  page shows the discounted total), then press checkout.
  See `shop.web.handle_web_checkout`.
- Mobile app: the code is entered on the payment screen and sent with the
  checkout request. See `shop.mobile.handle_app_checkout`.

Both end in `shop.checkout.checkout(cart, code=None)`, which returns a receipt.
