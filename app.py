import os
from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import sqlite3
import razorpay
from google.oauth2 import id_token
from google.auth.transport import requests as grequests
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "flavorfleet_secret")

# Razorpay credentials
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# Google OAuth client
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

# Database helper
DB_PATH = os.getenv("DATABASE_URL", "flavorfleet.db")
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# -----------------------------
# ROUTES
# -----------------------------

@app.route("/")
def landing():
    conn = get_db()
    restaurants = conn.execute("SELECT * FROM restaurants").fetchall()
    conn.close()
    return render_template("landing.html", restaurants=restaurants)

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

# -----------------------------
# CART ROUTES
# -----------------------------
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

@app.route("/add_to_cart/<int:item_id>")
def add_to_cart(item_id):
    conn = get_db()
    item = conn.execute("SELECT * FROM menu_items WHERE id=?", (item_id,)).fetchone()
    conn.close()
    if item and item["available"]:
        session.setdefault("cart", [])
        session["cart"].append(item_id)
    return redirect(request.referrer)

@app.route("/remove_from_cart/<int:item_id>")
def remove_from_cart(item_id):
    session.setdefault("cart", [])
    if item_id in session["cart"]:
        session["cart"].remove(item_id)
    return redirect("/cart")

@app.route('/cart_count')
def cart_count():
    count = len(session.get("cart", []))
    return jsonify({"count": count})
# -----------------------------
# CHECKOUT & PAYMENT
# -----------------------------
@app.route("/checkout")
def checkout():
    if "user" not in session:
        return redirect("/login")
    if not session.get("cart"):
        return "Your cart is empty."

    conn = get_db()
    items = []
    total_amount = 0
    unavailable = False

    for item_id in session["cart"]:
        item = conn.execute("SELECT * FROM menu_items WHERE id=?", (item_id,)).fetchone()
        if item:
            items.append(item)
            if item["available"]:
                total_amount += float(item["price"])
            else:
                unavailable = True
    conn.close()

    if unavailable:
        return "Some items are not available. Please remove them from cart."

    if total_amount <= 0:
        return "Cart total invalid."

    # Create Razorpay order
    try:
        razorpay_order = razorpay_client.order.create({
            "amount": int(total_amount * 100),
            "currency": "INR",
            "payment_capture": "1"
        })
    except Exception as e:
        print("Razorpay order creation failed:", e)
        return "Payment gateway error. Try again later."

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
        if not all(k in data for k in ["razorpay_payment_id","razorpay_order_id","razorpay_signature"]):
            return {"status":"error","msg":"Invalid payment data"}

        # Verify payment signature
        razorpay_client.utility.verify_payment_signature(data)

        conn = get_db()
        total_amount = 0

        # Only add order if items are available
        for item_id in session.get("cart", []):
            row = conn.execute("SELECT price, available FROM menu_items WHERE id=?", (item_id,)).fetchone()
            if row and row["available"]:
                total_amount += float(row["price"])

        if total_amount <= 0:
            return {"status":"error","msg":"Cart total invalid"}

        # Insert order
        conn.execute(
            "INSERT INTO orders(user_id,total_amount,status) VALUES(?,?,?)",
            (session["user"], total_amount, "Paid")
        )
        conn.commit()
        conn.close()

        # Clear cart
        session["cart"] = []

        return {"status":"success"}
    except Exception as e:
        print("Payment failed:", e)
        return {"status":"error","msg":str(e)}

# -----------------------------
# ORDERS, DASHBOARD, PROFILE
# -----------------------------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")
    return render_template("dashboard.html")

@app.route("/orders")
def orders():
    if "user" not in session:
        return redirect("/login")
    conn = get_db()
    orders = conn.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC", (session["user"],)).fetchall()
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

# -----------------------------
# REMINDERS
# -----------------------------
@app.route("/reminders", methods=["GET","POST"])
def reminders():
    if "user" not in session:
        return redirect("/login")
    conn = get_db()
    if request.method=="POST":
        message = request.form["message"]
        remind_time = request.form["remind_time"]
        conn.execute("INSERT INTO reminders(user,message,remind_time) VALUES(?,?,?)",
                     (session["user"], message, remind_time))
        conn.commit()
    reminders = conn.execute("SELECT * FROM reminders WHERE user=? ORDER BY id DESC",(session["user"],)).fetchall()
    conn.close()
    return render_template("reminders.html", reminders=reminders)

# -----------------------------
# SUBSCRIPTIONS
# -----------------------------
@app.route("/subscription", methods=["GET","POST"])
def subscription():
    if "user" not in session:
        return redirect("/login")
    conn = get_db()
    if request.method=="POST":
        plan = request.form["plan"]
        existing = conn.execute("SELECT * FROM subscriptions WHERE user=?",(session["user"],)).fetchone()
        if existing:
            conn.execute("UPDATE subscriptions SET plan=?, status='Active', start_date=? WHERE user=?",
                         (plan, datetime.now().strftime("%Y-%m-%d"), session["user"]))
        else:
            conn.execute("INSERT INTO subscriptions(user,plan,status,start_date) VALUES(?,?,?,?)",
                         (session["user"],plan,"Active", datetime.now().strftime("%Y-%m-%d")))
        conn.commit()
    subscription = conn.execute("SELECT * FROM subscriptions WHERE user=?",(session["user"],)).fetchone()
    conn.close()
    return render_template("subscription.html", subscription=subscription)

@app.route("/cancel_subscription")
def cancel_subscription():
    if "user" not in session:
        return redirect("/login")
    conn = get_db()
    conn.execute("UPDATE subscriptions SET status='Cancelled' WHERE user=?",(session["user"],))
    conn.commit()
    conn.close()
    return redirect("/subscription")

# -----------------------------
# LOGIN & REGISTER
# -----------------------------
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        email = request.form.get("email")
        password = request.form.get("password")
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=? AND password=?",(email,password)).fetchone()
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
        if not all([first_name,last_name,email,contact,password]):
            return "Please fill all fields"
        if password != confirm:
            return "Passwords do not match"
        conn = get_db()
        existing = conn.execute("SELECT * FROM users WHERE email=?",(email,)).fetchone()
        if existing:
            return "Email already registered"
        conn.execute("INSERT INTO users(first_name,last_name,email,contact,password) VALUES(?,?,?,?,?)",
                     (first_name,last_name,email,contact,password))
        conn.commit()
        conn.close()
        return redirect("/login")
    return render_template("register.html")

# -----------------------------
# GOOGLE LOGIN
# -----------------------------
@app.route("/google_login", methods=["POST"])
def google_login():
    token = request.json["token"]
    try:
        idinfo = id_token.verify_oauth2_token(token, grequests.Request(), GOOGLE_CLIENT_ID)
        email = idinfo["email"]
        name = idinfo["name"]
        first,last = (name.split(" ",1) + [""])[:2]
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=?",(email,)).fetchone()
        if not user:
            conn.execute("INSERT INTO users(first_name,last_name,email,contact,password) VALUES(?,?,?,?,?)",
                         (first,last,email,"","google_account"))
            conn.commit()
        session["user"] = first
        conn.close()
        return {"status":"success"}
    except Exception as e:
        print(e)
        return {"status":"error"}

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# -----------------------------
# SETTINGS
# -----------------------------
@app.route("/settings")
def settings():
    if "user" not in session:
        return redirect("/login")
    return render_template("settings.html")

# -----------------------------
# RUN SERVER
# -----------------------------
if __name__=="__main__":
    port = int(os.getenv("PORT",5000))
    app.run(host="0.0.0.0", port=port, debug=True)