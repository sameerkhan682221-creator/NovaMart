import os
import uuid
import requests

from flask import (
    Flask, request, session, redirect,
    url_for, render_template_string, flash
)

app = Flask(__name__)

app.secret_key = os.environ.get(
    "FLASK_SECRET",
    "novamart-demo-secret-change-before-deployment"
)

# RapidAPI settings
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "")
RAPIDAPI_HOST = "real-time-amazon-data.p.rapidapi.com"
RAPIDAPI_URL = f"https://{RAPIDAPI_HOST}/search"

# Demo products: clearly marked as demo products
DEMO_PRODUCTS = [
    {
        "id": "demo1",
        "title": "Wireless Bluetooth Headphones",
        "price": 1299,
        "image": "https://placehold.co/400x400?text=Headphones",
        "category": "Electronics",
        "rating": "4.3",
        "demo": True
    },
    {
        "id": "demo2",
        "title": "Smart Watch",
        "price": 1999,
        "image": "https://placehold.co/400x400?text=Smart+Watch",
        "category": "Electronics",
        "rating": "4.1",
        "demo": True
    },
    {
        "id": "demo3",
        "title": "Laptop Backpack",
        "price": 899,
        "image": "https://placehold.co/400x400?text=Backpack",
        "category": "Fashion",
        "rating": "4.2",
        "demo": True
    },
    {
        "id": "demo4",
        "title": "USB-C Fast Charger",
        "price": 499,
        "image": "https://placehold.co/400x400?text=Charger",
        "category": "Electronics",
        "rating": "4.0",
        "demo": True
    }
]

# In-memory product storage for this demo.
# Products added manually will reset when the server restarts.
PRODUCTS = {p["id"]: p for p in DEMO_PRODUCTS}


def get_product(product_id):
    """Find a product from our local demo list."""
    return PRODUCTS.get(str(product_id))


def rupees(amount):
    return "₹{:,.2f}".format(float(amount))


def get_cart():
    """Each visitor has their own cart in the Flask session."""
    return session.get("cart", {})


def cart_details():
    cart = get_cart()
    items = []
    total = 0

    for product_id, quantity in cart.items():
        product = get_product(product_id)

        if not product:
            continue

        quantity = max(1, int(quantity))
        price = float(product.get("price", 0))
        subtotal = price * quantity

        items.append({
            "product": product,
            "quantity": quantity,
            "subtotal": subtotal
        })

        total += subtotal

    return items, total


def search_amazon(query):
    """Fetch live product data from RapidAPI."""
    if not RAPIDAPI_KEY:
        return [], "RapidAPI key is not configured."

    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }

    params = {
        "query": query,
        "page": "1",
        "country": "IN"
    }

    try:
        response = requests.get(
            RAPIDAPI_URL,
            headers=headers,
            params=params,
            timeout=15
        )

        response.raise_for_status()
        data = response.json()

        # API response structure may vary.
        products = data.get("data", {}).get("products", [])

        if not products:
            products = data.get("products", [])

        results = []

        for item in products:
            title = item.get("product_title") or item.get("title")

            if not title:
                continue

            price_text = (
                item.get("product_price")
                or item.get("price")
                or "0"
            )

            # Convert price text to a number.
            price_text = str(price_text)
            price_text = (
                price_text.replace("₹", "")
                .replace("$", "")
                .replace(",", "")
                .strip()
            )

            try:
                price = float(price_text)
            except ValueError:
                price = 0

            image = (
                item.get("product_photo")
                or item.get("product_image")
                or item.get("thumbnail")
                or "https://placehold.co/400x400?text=No+Image"
            )

            product_id = str(
                item.get("asin")
                or item.get("product_id")
                or uuid.uuid4().hex[:12]
            )

            product = {
                "id": product_id,
                "title": title,
                "price": price,
                "image": image,
                "category": item.get("category", "Amazon"),
                "rating": item.get("product_star_rating", "N/A"),
                "demo": False,
                "source": "Amazon API"
            }

            PRODUCTS[product_id] = product
            results.append(product)

        return results, None

    except requests.RequestException:
        return [], "Could not connect to the product API."
    except Exception:
        return [], "The API returned an unexpected response."


BASE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport"
          content="width=device-width, initial-scale=1.0">

    <title>{{ title }} | NovaMart</title>

    <style>
        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            font-family: Arial, sans-serif;
            background: #f3f4f6;
            color: #222;
        }

        header {
            background: #131921;
            color: white;
            padding: 15px;
        }

        .header-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            flex-wrap: wrap;
        }

        .brand {
            font-size: 25px;
            font-weight: bold;
            color: #ffb84d;
            text-decoration: none;
        }

        .search {
            display: flex;
            flex: 1;
            min-width: 180px;
            max-width: 650px;
        }

        .search input {
            flex: 1;
            padding: 12px;
            border: 0;
            border-radius: 5px 0 0 5px;
            min-width: 0;
        }

        .search button {
            padding: 12px 16px;
            background: #febd69;
            border: 0;
            border-radius: 0 5px 5px 0;
            cursor: pointer;
        }

        nav {
            margin-top: 12px;
        }

        nav a {
            color: white;
            text-decoration: none;
            margin-right: 16px;
        }

        main {
            max-width: 1200px;
            margin: auto;
            padding: 18px;
        }

        .banner {
            background: linear-gradient(120deg, #232f3e, #40566e);
            color: white;
            padding: 25px;
            border-radius: 10px;
            margin-bottom: 20px;
        }

        .grid {
            display: grid;
            grid-template-columns:
                repeat(auto-fit, minmax(190px, 1fr));
            gap: 16px;
        }

        .card {
            background: white;
            padding: 14px;
            border-radius: 9px;
            box-shadow: 0 2px 8px #00000010;
        }

        .card img {
            width: 100%;
            height: 180px;
            object-fit: contain;
            background: #fff;
        }

        .card h3 {
            font-size: 16px;
            min-height: 42px;
        }

        .price {
            font-size: 20px;
            font-weight: bold;
            color: #b12704;
        }

        .btn {
            display: inline-block;
            background: #ffd814;
            color: #111;
            border: 0;
            border-radius: 20px;
            padding: 10px 16px;
            text-decoration: none;
            cursor: pointer;
            margin-top: 8px;
        }

        .btn.secondary {
            background: #e5e7eb;
        }

        .btn.dark {
            background: #232f3e;
            color: white;
        }

        .product-detail {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 25px;
            background: white;
            padding: 20px;
            border-radius: 10px;
        }

        .product-detail img {
            width: 100%;
            max-height: 400px;
            object-fit: contain;
        }

        .cart-row {
            display: grid;
            grid-template-columns: 90px 1fr;
            gap: 15px;
            background: white;
            padding: 15px;
            border-radius: 9px;
            margin-bottom: 12px;
        }

        .cart-row img {
            width: 90px;
            height: 90px;
            object-fit: contain;
        }

        input, select {
            padding: 10px;
            margin: 5px 0;
            max-width: 100%;
        }

        .message {
            background: #fff3cd;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 12px;
        }

        .muted {
            color: #666;
            font-size: 13px;
        }

        footer {
            text-align: center;
            padding: 25px;
            color: #666;
        }

        @media(max-width: 650px) {
            .product-detail {
                grid-template-columns: 1fr;
            }

            .header-row {
                align-items: stretch;
            }

            .search {
                max-width: 100%;
            }
        }
    </style>
</head>

<body>
<header>
    <div class="header-row">
        <a class="brand" href="/">NovaMart</a>

        <form class="search" action="/search" method="get">
            <input name="q"
                   placeholder="Search products..."
                   value="{{ search_query or '' }}"
                   required>

            <button type="submit">Search</button>
        </form>

        <a href="/cart" style="color:white;text-decoration:none">
            🛒 Cart ({{ cart_count }})
        </a>
    </div>

    <nav>
        <a href="/">Home</a>
        <a href="/add-product">Add Product</a>
        <a href="/wallet">Demo Wallet</a>
    </nav>
</header>

<main>
    {% with messages = get_flashed_messages() %}
        {% for message in messages %}
            <div class="message">{{ message }}</div>
        {% endfor %}
    {% endwith %}

    {{ content|safe }}
</main>

<footer>
    NovaMart Demo Store · Not affiliated with Amazon
    <br>
    Demo prices and wallet are not real transactions.
</footer>
</body>
</html>
"""


def page(title, content, search_query=""):
    cart = get_cart()
    cart_count = sum(int(q) for q in cart.values())

    return render_template_string(
        BASE_HTML,
        title=title,
        content=content,
        cart_count=cart_count,
        search_query=search_query
    )


def product_card(product):
    label = (
        "Live API product"
        if not product.get("demo")
        else "Demo product — sample price"
    )

    return f"""
    <div class="card">
        <a href="/product/{product['id']}">
            <img src="{product['image']}"
                 alt="Product image"
                 loading="lazy">
        </a>

        <p class="muted">{label}</p>

        <h3>{product['title']}</h3>

        <div class="price">{rupees(product['price'])}</div>

        <p>⭐ {product.get('rating', 'N/A')}</p>

        <a class="btn"
           href="/product/{product['id']}">
           View Product
        </a>

        <form action="/add-to-cart/{product['id']}"
              method="post">
            <button class="btn" type="submit">
                Add to Cart
            </button>
        </form>
    </div>
    """


@app.route("/")
def home():
    query = request.args.get("q", "").strip()

    products = list(PRODUCTS.values())
    content = """
    <div class="banner">
        <h1>Welcome to NovaMart</h1>
        <p>Discover products, explore categories and shop.</p>
        <p><b>Demo Store:</b> Sample prices are not real.</p>
    </div>
    """

    if query:
        products = [
            p for p in products
            if query.lower() in p["title"].lower()
            or query.lower() in p.get("category", "").lower()
        ]

    content += "<h2>Featured Products</h2><div class='grid'>"

    for product in products:
        content += product_card(product)

    content += "</div>"

    return page("Home", content, query)


@app.route("/search")
def search():
    query = request.args.get("q", "").strip()

    if not query:
        return redirect(url_for("home"))

    live_products, error = search_amazon(query)

    # Show local demo products too, if API has no result.
    products = live_products

    if not products:
        products = [
            p for p in PRODUCTS.values()
            if query.lower() in p["title"].lower()
        ]

    content = f"<h2>Search Results: {query}</h2>"

    if error:
        content += f"<div class='message'>{error}</div>"

    if not products:
        content += "<p>No products found. Try another search.</p>"
    else:
        content += "<div class='grid'>"

        for product in products:
            content += product_card(product)

        content += "</div>"

    return page("Search", content, query)


@app.route("/product/<product_id>")
def product_detail(product_id):
    product = get_product(product_id)

    if not product:
        return "Product not found", 404

    label = (
        "Live API price"
        if not product.get("demo")
        else "Demo price — sample only"
    )

    content = f"""
    <div class="product-detail">
        <div>
            <img src="{product['image']}" alt="Product">
        </div>

        <div>
            <h1>{product['title']}</h1>

            <p>⭐ {product.get('rating', 'N/A')}</p>

            <h2 class="price">{rupees(product['price'])}</h2>

            <p class="muted">{label}</p>

            <p>Category: {product.get('category', 'General')}</p>

            <form action="/add-to-cart/{product['id']}"
                  method="post">
                <button class="btn" type="submit">
                    Add to Cart
                </button>
            </form>

            <a class="btn secondary" href="/cart">
                Go to Cart
            </a>
        </div>
    </div>
    """

    # Related products
    related = [
        p for p in PRODUCTS.values()
        if p["id"] != product_id
        and p.get("category") == product.get("category")
    ][:4]

    if related:
        content += "<h2>Related Products</h2><div class='grid'>"

        for item in related:
            content += product_card(item)

        content += "</div>"

    return page(product["title"], content)


@app.route("/add-to-cart/<product_id>", methods=["POST"])
def add_to_cart(product_id):
    product = get_product(product_id)

    if not product:
        flash("Product not found.")
        return redirect(url_for("home"))

    cart = get_cart()
    cart[product_id] = int(cart.get(product_id, 0)) + 1

    session["cart"] = cart
    session.modified = True

    flash("Product added to your cart!")
    return redirect(request.referrer or url_for("home"))


@app.route("/cart")
def cart():
    items, total = cart_details()

    content = "<h1>Your Shopping Cart</h1>"

    if not items:
        content += """
        <p>Your cart is empty.</p>
        <a class="btn" href="/">Continue Shopping</a>
        """
        return page("Cart", content)

    for item in items:
        product = item["product"]
        product_id = product["id"]

        content += f"""
        <div class="cart-row">
            <img src="{product['image']}" alt="Product">

            <div>
                <h3>{product['title']}</h3>

                <p class="price">
                    {rupees(product['price'])}
                </p>

                <p>
                    Quantity: {item['quantity']}
                </p>

                <form action="/update-cart/{product_id}"
                      method="post"
                      style="display:inline">
                    <button class="btn secondary"
                            name="action"
                            value="decrease">
                        −
                    </button>

                    <button class="btn secondary"
                            name="action"
                            value="increase">
                        +
                    </button>
                </form>

                <form action="/remove-cart/{product_id}"
                      method="post"
                      style="display:inline">
                    <button class="btn secondary">
                        Remove
                    </button>
                </form>

                <p>
                    Subtotal: {rupees(item['subtotal'])}
                </p>
            </div>
        </div>
        """

    content += f"""
    <div class="card">
        <h2>Cart Total: {rupees(total)}</h2>

        <a class="btn dark" href="/checkout">
            Proceed to Checkout
        </a>

        <a class="btn secondary" href="/">
            Continue Shopping
        </a>
    </div>
    """

    return page("Shopping Cart", content)


@app.route("/update-cart/<product_id>", methods=["POST"])
def update_cart(product_id):
    cart = get_cart()
    action = request.form.get("action")

    if product_id in cart:
        quantity = int(cart[product_id])

        if action == "increase":
            quantity += 1

        elif action == "decrease":
            quantity -= 1

        if quantity <= 0:
            cart.pop(product_id, None)
        else:
            cart[product_id] = quantity

    session["cart"] = cart
    session.modified = True

    return redirect(url_for("cart"))


@app.route("/remove-cart/<product_id>", methods=["POST"])
def remove_cart(product_id):
    cart = get_cart()
    cart.pop(product_id, None)

    session["cart"] = cart
    session.modified = True

    flash("Product removed from cart.")
    return redirect(url_for("cart"))


@app.route("/add-product", methods=["GET", "POST"])
def add_product():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        price = request.form.get("price", "").strip()
        image = request.form.get("image", "").strip()
        category = request.form.get("category", "").strip()

        if not title or not price:
            flash("Product name and price are required.")
            return redirect(url_for("add_product"))

        try:
            price = float(price)

            if price < 0:
                raise ValueError

        except ValueError:
            flash("Please enter a valid positive price.")
            return redirect(url_for("add_product"))

        product_id = "custom_" + uuid.uuid4().hex[:10]

        product = {
            "id": product_id,
            "title": title,
            "price": price,
            "image": image or (
                "https://placehold.co/400x400?text=New+Product"
            ),
            "category": category or "General",
            "rating": "New",
            "demo": True
        }

        PRODUCTS[product_id] = product

        flash("Your demo product has been added!")
        return redirect(url_for("product_detail",
                                product_id=product_id))

    content = """
    <div class="card">
        <h1>Add a New Product</h1>

        <form method="post">
            <label>Product Name</label><br>
            <input name="title"
                   placeholder="Enter product name"
                   required><br>

            <label>Price in Rupees (Demo)</label><br>
            <input name="price"
                   type="number"
                   min="0"
                   step="0.01"
                   placeholder="Enter price"
                   required><br>

            <label>Image URL</label><br>
            <input name="image"
                   type="url"
                   placeholder="https://example.com/image.jpg"><br>

            <label>Category</label><br>
            <input name="category"
                   placeholder="Electronics, Fashion, etc."><br>

            <button class="btn" type="submit">
                Add Product
            </button>
        </form>
    </div>
    """

    return page("Add Product", content)


@app.route("/wallet")
def wallet():
    balance = float(session.get("wallet", 5000))

    content = f"""
    <div class="card">
        <h1>NovaMart Demo Wallet</h1>

        <h2 class="price">
            Balance: {rupees(balance)}
        </h2>

        <p>
            This is a demo wallet.
            It does not store or transfer real money.
        </p>

        <form action="/wallet/add" method="post">
            <input name="amount"
                   type="number"
                   min="1"
                   step="1"
                   placeholder="Amount to add"
                   required>

            <button class="btn" type="submit">
                Add Demo Money
            </button>
        </form>
    </div>
    """

    return page("Demo Wallet", content)


@app.route("/wallet/add", methods=["POST"])
def wallet_add():
    try:
        amount = float(request.form.get("amount", 0))

        if amount <= 0 or amount > 100000:
            raise ValueError

    except ValueError:
        flash("Enter a valid demo amount.")
        return redirect(url_for("wallet"))

    session["wallet"] = float(session.get("wallet", 5000)) + amount

    flash("Demo wallet balance updated.")
    return redirect(url_for("wallet"))


@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    items, total = cart_details()
    balance = float(session.get("wallet", 5000))

    if not items:
        flash("Your cart is empty.")
        return redirect(url_for("cart"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()

        if not name:
            flash("Please enter your name.")
            return redirect(url_for("checkout"))

        if balance < total:
            flash("Insufficient demo wallet balance.")
            return redirect(url_for("wallet"))

        session["wallet"] = balance - total

        order = {
            "id": "NM-" + uuid.uuid4().hex[:8].upper(),
            "name": name,
            "items": [
                {
                    "title": item["product"]["title"],
                    "price": item["product"]["price"],
                    "quantity": item["quantity"],
                    "subtotal": item["subtotal"]
                }
                for item in items
            ],
            "total": total
        }

        session["last_order"] = order
        session["cart"] = {}

        return redirect(url_for("invoice"))

    content = f"""
    <div class="card">
        <h1>Demo Checkout</h1>

        <h2>Total: {rupees(total)}</h2>

        <p>Demo Wallet Balance: {rupees(balance)}</p>

        <form method="post">
            <label>Your Name</label><br>

            <input name="name"
                   placeholder="Enter your name"
                   required><br>

            <button class="btn" type="submit">
                Place Demo Order
            </button>
        </form>

        <p class="muted">
            No real payment will be made.
        </p>
    </div>
    """

    return page("Checkout", content)


@app.route("/invoice")
def invoice():
    order = session.get("last_order")

    if not order:
        return redirect(url_for("home"))

    content = f"""
    <div class="card">
        <h1>Order Confirmed!</h1>

        <h2>Invoice</h2>

        <p>Order ID: {order['id']}</p>

        <p>Customer: {order['name']}</p>

        <hr>
    """

    for item in order["items"]:
        content += f"""
        <p>
            {item['title']}
            × {item['quantity']}
            = {rupees(item['subtotal'])}
        </p>
        """

    content += f"""
        <hr>

        <h2>Total: {rupees(order['total'])}</h2>

        <p class="muted">
            This is a demo invoice. No real transaction occurred.
        </p>

        <button class="btn" onclick="window.print()">
            Print Invoice
        </button>

        <a class="btn secondary" href="/">
            Continue Shopping
        </a>
    </div>
    """

    return page("Invoice", content)


@app.errorhandler(404)
def not_found(error):
    return page(
        "Not Found",
        "<h1>404</h1><p>Page not found.</p>"
        "<a class='btn' href='/'>Go Home</a>"
    )


if __name__ == "__main__":
    # Local testing only. Public deployment uses Gunicorn.
    app.run(host="0.0.0.0", port=5000, debug=False)
