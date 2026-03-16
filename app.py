import os
from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
import razorpay  # Razorpay integration
from google.oauth2 import id_token
from google.auth.transport import requests as grequests

RAZORPAY_KEY_ID = "YOUR_KEY_ID"
RAZORPAY_KEY_SECRET = "YOUR_KEY_SECRET"

razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

app = Flask(__name__)
app.secret_key = "flavorfleet_secret"

GOOGLE_CLIENT_ID = "461666237020-v9q25vcpdtl9ui9rrff101ce5lhp1mqb.apps.googleusercontent.com"

# DATABASE CONNECTION
def get_db():
    conn = sqlite3.connect("flavorfleet.db")
    conn.row_factory = sqlite3.Row
    return conn

# HOME / LANDING
@app.route("/")
def landing():
    return render_template("landing.html")

# DASHBOARD
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")
    conn = get_db()
    restaurants = conn.execute("SELECT * FROM restaurants").fetchall()
    conn.close()
    return render_template("dashboard.html", username=session["user"], restaurants=restaurants)

# RESTAURANTS
@app.route("/restaurants")
def restaurants():
    conn = get_db()
    restaurants = conn.execute("SELECT * FROM restaurants").fetchall()
    conn.close()
    return render_template("restaurants.html", restaurants=restaurants)

# RESTAURANT MENU
@app.route("/restaurant/<int:restaurant_id>")
def restaurant_menu(restaurant_id):
    conn = get_db()
    restaurant = conn.execute("SELECT * FROM restaurants WHERE id=?", (restaurant_id,)).fetchone()
    items = conn.execute("SELECT * FROM menu_items WHERE restaurant_id=?", (restaurant_id,)).fetchall()
    categories = conn.execute("SELECT DISTINCT category FROM menu_items WHERE restaurant_id=?", (restaurant_id,)).fetchall()
    conn.close()
    return render_template("menu.html", restaurant=restaurant, items=items, categories=categories)

# ADD TO CART
@app.route("/add_to_cart/<int:item_id>")
def add_to_cart(item_id):
    if "cart" not in session:
        session["cart"] = []
    cart = session["cart"]
    cart.append(item_id)
    session["cart"] = cart
    return redirect(request.referrer)

# CART PAGE
@app.route("/cart")
def cart():
    if "cart" not in session:
        session["cart"] = []
    conn = get_db()
    items = []
    for item_id in session["cart"]:
        item = conn.execute("SELECT * FROM menu_items WHERE id=?", (item_id,)).fetchone()
        if item:
            items.append(item)
    conn.close()
    return render_template("cart.html", items=items)

# REMOVE FROM CART
@app.route("/remove_from_cart/<int:item_id>")
def remove_from_cart(item_id):
    if "cart" not in session:
        return redirect("/cart")
    cart = session["cart"]
    if item_id in cart:
        cart.remove(item_id)
    session["cart"] = cart
    return redirect("/cart")

# CHECKOUT
@app.route("/checkout")
def checkout():
    if "user" not in session:
        return redirect("/login")
    if "cart" not in session or len(session["cart"]) == 0:
        return "Your cart is empty"

    conn = get_db()
    total_amount = 0
    items = []

    for item_id in session["cart"]:
        item = conn.execute("SELECT * FROM menu_items WHERE id=?", (item_id,)).fetchone()
        if item and item["price"] is not None:
            items.append(item)
            total_amount += float(item["price"])  # ensure numeric

    conn.close()

    if total_amount <= 0:
        return "Cart total invalid. Please check items."

    # Razorpay order creation with try/except
    try:
        razorpay_order = razorpay_client.order.create({
            "amount": int(total_amount * 100),  # in paise
            "currency": "INR",
            "payment_capture": "1"
        })
    except Exception as e:
        print("Razorpay order creation failed:", e)
        return "Payment gateway error. Please try again later."

    return render_template(
        "checkout.html",
        items=items,
        total=total_amount,
        razorpay_order_id=razorpay_order["id"],
        razorpay_key_id=RAZORPAY_KEY_ID
    )
# ORDERS
@app.route("/orders")
def orders():
    if "user" not in session:
        return redirect("/login")
    conn = get_db()
    orders = conn.execute("SELECT * FROM orders WHERE user=? ORDER BY id DESC", (session["user"],)).fetchall()
    conn.close()
    return render_template("orders.html", orders=orders)

# REMINDERS
@app.route("/reminders", methods=["GET","POST"])
def reminders():
    if "user" not in session:
        return redirect("/login")
    conn = get_db()
    if request.method == "POST":
        message = request.form["message"]
        remind_time = request.form["remind_time"]
        conn.execute("INSERT INTO reminders (user, message, remind_time) VALUES (?,?,?)",
                     (session["user"], message, remind_time))
        conn.commit()
    reminders = conn.execute("SELECT * FROM reminders WHERE user=?", (session["user"],)).fetchall()
    conn.close()
    return render_template("reminders.html", reminders=reminders)

# SUBSCRIPTION
@app.route("/subscription", methods=["GET","POST"])
def subscription():
    if "user" not in session:
        return redirect("/login")
    conn = get_db()
    sub = conn.execute("SELECT * FROM subscriptions WHERE user=?", (session["user"],)).fetchone()
    if request.method == "POST":
        plan = request.form["plan"]
        if sub:
            conn.execute("UPDATE subscriptions SET plan=?, status='Active', start_date=date('now') WHERE user=?",
                         (plan, session["user"]))
        else:
            conn.execute("INSERT INTO subscriptions (user, plan, status, start_date) VALUES (?,?,?,date('now'))",
                         (session["user"], plan, "Active"))
        conn.commit()
    sub = conn.execute("SELECT * FROM subscriptions WHERE user=?", (session["user"],)).fetchone()
    conn.close()
    return render_template("subscription.html", subscription=sub)

@app.route("/cancel_subscription")
def cancel_subscription():
    if "user" not in session:
        return redirect("/login")
    conn = get_db()
    conn.execute("UPDATE subscriptions SET status='Cancelled' WHERE user=?", (session["user"],))
    conn.commit()
    conn.close()
    return redirect("/subscription")

# PROFILE
@app.route("/profile", methods=["GET","POST"])
def profile():
    if "user" not in session:
        return redirect("/login")
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE first_name=?", (session["user"],)).fetchone()
    if request.method == "POST":
        first = request.form["first_name"]
        last = request.form["last_name"]
        email = request.form["email"]
        contact = request.form["contact"]
        conn.execute("UPDATE users SET first_name=?, last_name=?, email=?, contact=? WHERE first_name=?",
                     (first,last,email,contact,session["user"]))
        conn.commit()
        session["user"] = first
    conn.close()
    return render_template("profile.html", user=user)

# LOGIN
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (email,password)).fetchone()
        conn.close()
        if user:
            session["user"] = user["first_name"]
            return redirect("/dashboard")
        return "Invalid credentials"
    return render_template("login.html")

# REGISTER
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        contact = request.form.get("contact")
        password = request.form.get("password")
        confirm = request.form.get("confirm_password")
        if not first_name or not last_name or not email or not contact or not password:
            return "Please fill all fields"
        if password != confirm:
            return "Passwords do not match"
        conn = get_db()
        existing = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if existing:
            return "Email already registered"
        conn.execute("INSERT INTO users(first_name,last_name,email,contact,password) VALUES(?,?,?,?,?)",
                     (first_name,last_name,email,contact,password))
        conn.commit()
        conn.close()
        return redirect("/login")
    return render_template("register.html")

# GOOGLE LOGIN
@app.route("/google_login", methods=["POST"])
def google_login():
    token = request.json["token"]
    try:
        idinfo = id_token.verify_oauth2_token(token, grequests.Request(), GOOGLE_CLIENT_ID)
        email = idinfo["email"]
        name = idinfo["name"]
        names = name.split(" ",1)
        first_name = names[0]
        last_name = names[1] if len(names)>1 else ""
        conn = get_db()
        cur = conn.cursor()
        user = cur.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if not user:
            cur.execute("INSERT INTO users (first_name,last_name,email,contact,password) VALUES (?,?,?,?,?)",
                        (first_name,last_name,email,"","google_account"))
            conn.commit()
        session["user"] = first_name
        return {"status":"success"}
    except Exception as e:
        print(e)
        return {"status":"error"}

# SETTINGS
@app.route("/settings")
def settings():
    return render_template("settings.html")

# LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# PAYMENT SUCCESS
@app.route("/payment_success", methods=["POST"])
def payment_success():
    data = request.json

    try:
        # Ensure keys exist
        if not all(k in data for k in ["razorpay_payment_id", "razorpay_order_id", "razorpay_signature"]):
            return {"status": "error", "msg": "Invalid payment data"}

        # Verify payment signature
        razorpay_client.utility.verify_payment_signature(data)

        conn = get_db()
        total_amount = 0
        for item_id in session.get("cart", []):
            row = conn.execute("SELECT price FROM menu_items WHERE id=?", (item_id,)).fetchone()
            if row and row["price"] is not None:
                total_amount += float(row["price"])

        conn.execute(
            "INSERT INTO orders(user,total_amount,status) VALUES(?,?,?)",
            (session["user"], total_amount, "Paid")
        )
        conn.commit()
        conn.close()

        session["cart"] = []

        return {"status": "success"}

    except Exception as e:
        print("Payment failed:", e)
        return {"status": "error", "msg": str(e)}

@app.route("/payment_done")
def payment_done():
    total = request.args.get("total", 0)
    return render_template("payment_success.html", total=total)

@app.route("/check_packages")
def check_packages():
    import razorpay
    return f"Razorpay installed: {razorpay.__version__}"

# CART COUNT API for floating cart
@app.route("/cart_count")
def cart_count():
    count = len(session.get("cart", []))
    return {"count": count}

# RUN SERVER
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)