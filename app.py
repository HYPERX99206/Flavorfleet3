from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3

app = Flask(__name__)
app.secret_key = "flavorfleet_secret"


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


# LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            return "Please fill all fields"

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        ).fetchone()

        conn.close()

        if user:
            session["user"] = username
            return redirect("/dashboard")
        else:
            return "Invalid username or password"

    return render_template("login.html")


# REGISTER
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            return "Please fill all fields"

        conn = get_db()

        existing = conn.execute(
            "SELECT * FROM users WHERE username=?",
            (username,)
        ).fetchone()

        if existing:
            conn.close()
            return "User already exists"

        conn.execute(
            "INSERT INTO users(username,password) VALUES(?,?)",
            (username, password)
        )

        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("register.html")


# ORDERS
@app.route("/orders")
def orders():

    if "user" not in session:
        return redirect("/login")

    return render_template("orders.html")


# SETTINGS
@app.route("/settings")
def settings():

    if "user" not in session:
        return redirect("/login")

    return render_template("settings.html")


# SUBSCRIPTIONS
@app.route("/subscriptions")
def subscriptions():

    if "user" not in session:
        return redirect("/login")

    conn = get_db()

    subs = conn.execute(
        "SELECT * FROM subscriptions WHERE user=?",
        (session["user"],)
    ).fetchall()

    conn.close()

    return render_template("subscriptions.html", subs=subs)


# ADD SUBSCRIPTION
@app.route("/add_subscription", methods=["POST"])
def add_subscription():

    if "user" not in session:
        return redirect("/login")

    plan = request.form.get("plan")

    conn = get_db()

    conn.execute(
        "INSERT INTO subscriptions(user,plan,status,start_date) VALUES(?,?,?,date('now'))",
        (session["user"], plan, "active")
    )

    conn.commit()
    conn.close()

    return redirect("/subscriptions")


# REMINDERS
@app.route("/reminders")
def reminders():

    if "user" not in session:
        return redirect("/login")

    conn = get_db()

    data = conn.execute(
        "SELECT * FROM reminders WHERE user=?",
        (session["user"],)
    ).fetchall()

    conn.close()

    return render_template("reminders.html", reminders=data)


# ADD REMINDER
@app.route("/add_reminder", methods=["POST"])
def add_reminder():

    if "user" not in session:
        return redirect("/login")

    msg = request.form.get("message")
    time = request.form.get("time")

    conn = get_db()

    conn.execute(
        "INSERT INTO reminders(user,message,remind_time) VALUES(?,?,?)",
        (session["user"], msg, time)
    )

    conn.commit()
    conn.close()

    return redirect("/reminders")


# LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# RUN SERVER
if __name__ == "__main__":
    app.run(debug=True)