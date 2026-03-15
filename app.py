from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
from google.oauth2 import id_token
from google.auth.transport import requests as grequests

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

    restaurants = conn.execute(
        "SELECT * FROM restaurants"
    ).fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        username=session["user"],
        restaurants=restaurants
    )


# RESTAURANTS
@app.route("/restaurants")
def restaurants():

    conn = get_db()

    restaurants = conn.execute(
        "SELECT * FROM restaurants"
    ).fetchall()

    conn.close()

    return render_template(
        "restaurants.html",
        restaurants=restaurants
    )


# RESTAURANT MENU
@app.route("/restaurant/<int:restaurant_id>")
def restaurant_menu(restaurant_id):

    conn = get_db()

    restaurant = conn.execute(
        "SELECT * FROM restaurants WHERE id=?",
        (restaurant_id,)
    ).fetchone()

    items = conn.execute(
        "SELECT * FROM menu_items WHERE restaurant_id=?",
        (restaurant_id,)
    ).fetchall()

    categories = conn.execute(
        "SELECT DISTINCT category FROM menu_items WHERE restaurant_id=?",
        (restaurant_id,)
    ).fetchall()

    conn.close()

    return render_template(
        "menu.html",
        restaurant=restaurant,
        items=items,
        categories=categories
    )


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

        item = conn.execute(
            "SELECT * FROM menu_items WHERE id=?",
            (item_id,)
        ).fetchone()

        if item:
            items.append(item)

    conn.close()

    return render_template(
        "cart.html",
        items=items
    )


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

    session["cart"] = []

    return render_template("checkout.html")


# ORDERS
@app.route("/orders")
def orders():
    return render_template("orders.html")


# REMINDERS
@app.route("/reminders")
def reminders():
    return render_template("reminders.html")


# SUBSCRIPTION
@app.route("/subscription")
def subscription():
    return render_template("subscription.html")

# PROFILE
@app.route("/profile")
def profile():
    return render_template("profile.html")


# LOGIN
@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email")
        password = request.form.get("password")

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE email=? AND password=?",
            (email,password)
        ).fetchone()

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

        existing = conn.execute(
            "SELECT * FROM users WHERE email=?",
            (email,)
        ).fetchone()

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


# GOOGLE LOGIN
@app.route("/google_login", methods=["POST"])
def google_login():

    token = request.json["token"]

    try:
        idinfo = id_token.verify_oauth2_token(
            token,
            grequests.Request(),
            GOOGLE_CLIENT_ID
        )

        email = idinfo["email"]
        name = idinfo["name"]

        names = name.split(" ",1)
        first_name = names[0]
        last_name = names[1] if len(names)>1 else ""

        conn = get_db()
        cur = conn.cursor()

        user = cur.execute(
            "SELECT * FROM users WHERE email=?",
            (email,)
        ).fetchone()

        if not user:
            cur.execute(
                "INSERT INTO users (first_name,last_name,email,contact,password) VALUES (?,?,?,?,?)",
                (first_name,last_name,email,"","google_account")
            )
            conn.commit()

        session["user"] = first_name

        return {"status":"success"}

    except Exception as e:
        print(e)
        return {"status":"error"}


# LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# RUN SERVER
if __name__ == "__main__":
    app.run(debug=True)