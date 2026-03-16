import os
from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import sqlite3
import razorpay
from google.oauth2 import id_token
from google.auth.transport import requests as grequests
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

# App & secret
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "flavorfleet_secret")

# Razorpay credentials from .env
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# Google OAuth
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

# Database connection
DB_PATH = os.getenv("DATABASE_URL", "flavorfleet.db")
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# -----------------------
# ROUTES
# -----------------------

@app.route("/")
def landing():
    try:
        conn = get_db()
        restaurants = conn.execute("SELECT * FROM restaurants WHERE available=1").fetchall()
        conn.close()
        return render_template("landing.html", restaurants=restaurants)
    except Exception as e:
        print("Landing error:", e)
        return "Something went wrong. Please try later."

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")
    try:
        conn = get_db()
        restaurants = conn.execute("SELECT * FROM restaurants WHERE available=1").fetchall()
        conn.close()
        return render_template("dashboard.html", username=session["user"], restaurants=restaurants)
    except Exception as e:
        print("Dashboard error:", e)
        return "Something went wrong."

@app.route("/restaurants")
def restaurants():
    try:
        conn = get_db()
        restaurants = conn.execute("SELECT * FROM restaurants WHERE available=1").fetchall()
        conn.close()
        return render_template("restaurants.html", restaurants=restaurants)
    except Exception as e:
        print("Restaurants error:", e)
        return "Something went wrong."

@app.route("/restaurant/<int:restaurant_id>")
def restaurant_menu(restaurant_id):
    try:
        conn = get_db()
        restaurant = conn.execute("SELECT * FROM restaurants WHERE id=? AND available=1", (restaurant_id,)).fetchone()
        if not restaurant:
            conn.close()
            return "Restaurant not available."
        items = conn.execute("SELECT * FROM menu_items WHERE restaurant_id=? AND available=1", (restaurant_id,)).fetchall()
        categories = conn.execute("SELECT DISTINCT category FROM menu_items WHERE restaurant_id=? AND available=1", (restaurant_id,)).fetchall()
        conn.close()
        return render_template("menu.html", restaurant=restaurant, items=items, categories=categories)
    except Exception as e:
        print("Menu error:", e)
        return "Something went wrong."

# -----------------------
# CART
# -----------------------
@app.route("/add_to_cart/<int:item_id>")
def add_to_cart(item_id):
    session.setdefault("cart", [])
    session["cart"].append(item_id)
    return redirect(request.referrer or "/")

@app.route("/remove_from_cart/<int:item_id>")
def remove_from_cart(item_id):
    session.setdefault("cart", [])
    if item_id in session["cart"]:
        session["cart"].remove(item_id)
    return redirect("/cart")

@app.route("/cart")
def cart():
    session.setdefault("cart", [])
    items = []
    try:
        conn = get_db()
        for item_id in session["cart"]:
            item = conn.execute("SELECT * FROM menu_items WHERE id=? AND available=1", (item_id,)).fetchone()
            if item:
                items.append(item)
        conn.close()
        return render_template("cart.html", items=items)
    except Exception as e:
        print("Cart error:", e)
        return "Something went wrong."

# -----------------------
# CHECKOUT
# -----------------------
@app.route("/checkout")
def checkout():
    if "user" not in session:
        return redirect("/login")
    session.setdefault("cart", [])
    if not session["cart"]:
        return "Your cart is empty."

    try:
        conn = get_db()
        items = []
        total_amount = 0
        for item_id in session["cart"]:
            item = conn.execute("SELECT * FROM menu_items WHERE id=? AND available=1", (item_id,)).fetchone()
            if item and item["price"]:
                items.append(item)
                total_amount += float(item["price"])
        conn.close()

        if total_amount <= 0:
            return "Cart total invalid. Please check items."

        razorpay_order = razorpay_client.order.create({
            "amount": int(total_amount * 100),
            "currency": "INR",
            "payment_capture": "1"
        })

        return render_template(
            "checkout.html",
            items=items,
            total=total_amount,
            razorpay_order_id=razorpay_order["id"],
            razorpay_key_id=RAZORPAY_KEY_ID
        )
    except Exception as e:
        print("Checkout error:", e)
        return "Payment gateway error. Try later."

@app.route("/payment_success", methods=["POST"])
def payment_success():
    data = request.json
    try:
        if not all(k in data for k in ["razorpay_payment_id", "razorpay_order_id", "razorpay_signature"]):
            return {"status": "error", "msg": "Invalid payment data"}

        razorpay_client.utility.verify_payment_signature(data)

        conn = get_db()
        total_amount = 0
        for item_id in session.get("cart", []):
            row = conn.execute("SELECT price FROM menu_items WHERE id=? AND available=1", (item_id,)).fetchone()
            if row and row["price"] is not None:
                total_amount += float(row["price"])

        if total_amount <= 0:
            return {"status": "error", "msg": "Cart empty or items unavailable"}

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

# -----------------------
# ORDERS
# -----------------------
@app.route("/orders")
def orders():
    if "user" not in session:
        return redirect("/login")
    try:
        conn = get_db()
        orders = conn.execute("SELECT * FROM orders WHERE user=? ORDER BY id DESC", (session["user"],)).fetchall()
        conn.close()
        return render_template("orders.html", orders=orders)
    except Exception as e:
        print("Orders error:", e)
        return "Something went wrong."

# -----------------------
# AUTH
# -----------------------
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        email = request.form.get("email")
        password = request.form.get("password")
        try:
            conn = get_db()
            user = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (email,password)).fetchone()
            conn.close()
            if user:
                session["user"] = user["first_name"]
                return redirect("/dashboard")
            return "Invalid credentials"
        except Exception as e:
            print("Login error:", e)
            return "Login failed."
    return render_template("login.html")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method=="POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        contact = request.form.get("contact")
        password = request.form.get("password")
        confirm = request.form.get("confirm_password")
        if not all([first_name,last_name,email,contact,password]):
            return "Please fill all fields"
        if password != confirm:
            return "Passwords do not match"
        try:
            conn = get_db()
            existing = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
            if existing:
                conn.close()
                return "Email already registered"
            conn.execute(
                "INSERT INTO users(first_name,last_name,email,contact,password) VALUES(?,?,?,?,?)",
                (first_name,last_name,email,contact,password)
            )
            conn.commit()
            conn.close()
            return redirect("/login")
        except Exception as e:
            print("Register error:", e)
            return "Registration failed."
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# -----------------------
# CART COUNT
# -----------------------
@app.route("/cart_count")
def cart_count():
    return jsonify({"count": len(session.get("cart", []))})

# -----------------------
# RUN SERVER
# -----------------------
if __name__=="__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)