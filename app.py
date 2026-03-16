import os
from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import sqlite3
import razorpay  # Razorpay integration
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
    return render_template("landing.html")

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")
    conn = get_db()
    restaurants = conn.execute("SELECT * FROM restaurants").fetchall()
    conn.close()
    return render_template("dashboard.html", username=session["user"], restaurants=restaurants)

@app.route("/restaurants")
def restaurants():
    conn = get_db()
    restaurants = conn.execute("SELECT * FROM restaurants").fetchall()
    conn.close()
    return render_template("restaurants.html", restaurants=restaurants)

@app.route("/restaurant/<int:restaurant_id>")
def restaurant_menu(restaurant_id):
    conn = get_db()
    restaurant = conn.execute("SELECT * FROM restaurants WHERE id=?", (restaurant_id,)).fetchone()
    items = conn.execute("SELECT * FROM menu_items WHERE restaurant_id=?", (restaurant_id,)).fetchall()
    categories = conn.execute("SELECT DISTINCT category FROM menu_items WHERE restaurant_id=?", (restaurant_id,)).fetchall()
    conn.close()
    return render_template("menu.html", restaurant=restaurant, items=items, categories=categories)

@app.route("/add_to_cart/<int:item_id>")
def add_to_cart(item_id):
    session.setdefault("cart", [])
    session["cart"].append(item_id)
    return redirect(request.referrer)

@app.route("/cart")
def cart():
    session.setdefault("cart", [])
    conn = get_db()
    items = []
    for item_id in session["cart"]:
        item = conn.execute("SELECT * FROM menu_items WHERE id=?", (item_id,)).fetchone()
        if item:
            items.append(item)
    conn.close()
    return render_template("cart.html", items=items)

@app.route("/remove_from_cart/<int:item_id>")
def remove_from_cart(item_id):
    session.setdefault("cart", [])
    if item_id in session["cart"]:
        session["cart"].remove(item_id)
    return redirect("/cart")

# -----------------------
# Checkout & Payment
# -----------------------
@app.route("/checkout")
def checkout():
    if "user" not in session:
        return redirect("/login")
    if not session.get("cart"):
        return "Your cart is empty."

    conn = get_db()
    items = []
    total_amount = 0
    for item_id in session["cart"]:
        item = conn.execute("SELECT * FROM menu_items WHERE id=?", (item_id,)).fetchone()
        if item and item["price"]:
            items.append(item)
            total_amount += float(item["price"])
    conn.close()

    if total_amount <= 0:
        return "Cart total invalid. Please check items."

    # Razorpay order creation
    try:
        razorpay_order = razorpay_client.order.create({
            "amount": int(total_amount * 100),  # paise
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

@app.route("/payment_success", methods=["POST"])
def payment_success():
    data = request.json
    try:
        # Verify that required keys exist
        if not all(k in data for k in ["razorpay_payment_id", "razorpay_order_id", "razorpay_signature"]):
            return jsonify({"status": "error", "msg": "Invalid payment data"})

        razorpay_client.utility.verify_payment_signature(data)

        # Record order
        conn = get_db()
        total_amount = 0
        for item_id in session.get("cart", []):
            row = conn.execute("SELECT price FROM menu_items WHERE id=?", (item_id,)).fetchone()
            if row and row["price"]:
                total_amount += float(row["price"])

        conn.execute(
            "INSERT INTO orders(user,total_amount,status) VALUES(?,?,?)",
            (session["user"], total_amount, "Paid")
        )
        conn.commit()
        conn.close()

        session["cart"] = []
        return jsonify({"status": "success"})

    except Exception as e:
        print("Payment failed:", e)
        return jsonify({"status": "error", "msg": str(e)})

@app.route("/payment_done")
def payment_done():
    total = request.args.get("total", 0)
    return render_template("payment_success.html", total=total)

# -----------------------
# Orders, Profile, Login, Register
# -----------------------
@app.route("/orders")
def orders():
    if "user" not in session:
        return redirect("/login")
    conn = get_db()
    orders = conn.execute("SELECT * FROM orders WHERE user=? ORDER BY id DESC", (session["user"],)).fetchall()
    conn.close()
    return render_template("orders.html", orders=orders)

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

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
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

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method=="POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        contact = request.form.get("contact")
        password = request.form.get("password")
        confirm = request.form.get("confirm_password")
        if not all([first_name, last_name, email, contact, password]):
            return "Please fill all fields"
        if password != confirm:
            return "Passwords do not match"
        conn = get_db()
        existing = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if existing:
            return "Email already registered"
        conn.execute(
            "INSERT INTO users(first_name,last_name,email,contact,password) VALUES(?,?,?,?,?)",
            (first_name,last_name,email,contact,password)
        )
        conn.commit()
        conn.close()
        return redirect("/login")
    return render_template("register.html")

# Google OAuth
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
            cur.execute("INSERT INTO users(first_name,last_name,email,contact,password) VALUES(?,?,?,?,?)",
                        (first_name,last_name,email,"","google_account"))
            conn.commit()
        session["user"] = first_name
        return {"status":"success"}
    except Exception as e:
        print(e)
        return {"status":"error"}

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# -----------------------
# Floating Cart Count API
# -----------------------
@app.route("/cart_count")
def cart_count():
    return jsonify({"count": len(session.get("cart", []))})

# -----------------------
# Run Server
# -----------------------
if __name__=="__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)