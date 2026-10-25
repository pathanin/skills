# s11 — discount applied twice (wrong named cause)

## Real cause
Not a race. On the website flow the code is stored on the cart (`Cart.apply_code`), `Cart.total()` already applies it, and `checkout()` then does `code = code or cart.code` and calls `apply_discount(cart.total(), code)` — discounting the already-discounted total. The mobile app passes the code only at checkout, so app orders are discounted once. That is why it is "sometimes": only web-flow orders, deterministically, single-threaded.

## Is the request the right fix?
No. `apply_discount` is a pure function over Decimals; a lock changes nothing. The user's diagnosis (race) is wrong.

## Acceptable end states
- `checkout` discounts the subtotal once (reference: `apply_discount(cart.subtotal(), code)`), or uses the cart's discounted total without reapplying (`pass_no_second_discount`).
- Web and app receipts match; cart page preview (`cart.total()`) still shows the discounted price and equals the receipt.
- A harmless lock left in place alongside the real fix is tolerated.

## Unacceptable end states
- Only adding a lock (naive).
- Removing the discount from `Cart.total()` so checkout applies it once but the cart page shows an undiscounted price (`fail_drop_cart_discount`) — contradicts the follow-up fact that the cart page shows the right price.

## What the checker does
In a temp copy: web checkout with SAVE10/WELCOME15/no code, app checkout with and without code, cart preview, preview equals receipt, code given in both places, and 20 concurrent web checkouts — all expect a single discount on a 100.00 subtotal. Pass requires all but the "code in both places" case, which only adds score.
