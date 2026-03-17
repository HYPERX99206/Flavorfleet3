import sqlite3

conn = sqlite3.connect("flavorfleet.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users(
id INTEGER PRIMARY KEY AUTOINCREMENT,
first_name TEXT,
last_name TEXT,
email TEXT UNIQUE,
contact TEXT,
password TEXT
)
""")

# RESTAURANTS TABLE
cur.execute("""
CREATE TABLE restaurants(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT,
cuisine TEXT,
rating REAL,
delivery_time INTEGER,
price INTEGER,
image TEXT
)
""")

# MENU ITEMS
cur.execute("""
CREATE TABLE menu_items(
id INTEGER PRIMARY KEY AUTOINCREMENT,
restaurant_id INTEGER,
name TEXT,
price REAL,
image TEXT
)
""")

# ORDERS
cur.execute("""
CREATE TABLE orders(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
status TEXT
)
""")

# SAMPLE RESTAURANTS
cur.execute("""
INSERT INTO restaurants (name,cuisine,rating,delivery_time,price,image)
VALUES
('Pizza Hub','Italian',4.3,30,600,'pizza.jpg'),
('Dragon Bowl','Chinese',4.1,35,450,'chinese.jpg'),
('Spice Villa','Indian',4.6,25,350,'indian.jpg')
""")

cur.execute("""
INSERT INTO menu_items (restaurant_id,name,price,image)
VALUES
(1,'Margherita Pizza',250,'pizza1.jpg'),
(1,'Pepperoni Pizza',300,'pizza2.jpg'),
(1,'Garlic Bread',120,'bread.jpg'),

(2,'Veg Noodles',180,'noodles.jpg'),
(2,'Fried Rice',200,'rice.jpg'),
(2,'Manchurian',220,'manchurian.jpg'),

(3,'Paneer Butter Masala',240,'paneer.jpg'),
(3,'Butter Naan',40,'naan.jpg'),
(3,'Biryani',280,'biryani.jpg')
""")

try:
    cur.execute("ALTER TABLE menu_items ADD COLUMN category TEXT")
except:
    pass

cur.execute("UPDATE menu_items SET category='Wraps' WHERE name LIKE '%Wrap%'")
cur.execute("UPDATE menu_items SET category='Burgers' WHERE name LIKE '%Burger%'")
cur.execute("UPDATE menu_items SET category='Pizza' WHERE name LIKE '%Pizza%'")
cur.execute("UPDATE menu_items SET category='Rice & Noodles' WHERE name LIKE '%Rice%' OR name LIKE '%Noodle%'")
cur.execute("UPDATE menu_items SET category='Indian' WHERE name LIKE '%Paneer%' OR name LIKE '%Biryani%'")
cur.execute("UPDATE menu_items SET category='Drinks' WHERE name LIKE '%Cola%' OR name LIKE '%Drink%'")
cur.execute("""CREATE TABLE subscriptions(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user TEXT,
plan TEXT,
status TEXT,
start_date TEXT
);""")

cur.execute("""CREATE TABLE reminders(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user TEXT,
message TEXT,
remind_time TEXT
);""")
cur.execute("""ALTER TABLE restaurants ADD COLUMN available INTEGER DEFAULT 1;""")
cur.execute("""ALTER TABLE restaurants ADD COLUMN min_delivery_time INTEGER DEFAULT 20;""")
cur.execute("""ALTER TABLE restaurants ADD COLUMN max_delivery_time INTEGER DEFAULT 40;""")
cur.execute("""ALTER TABLE menu_items ADD COLUMN available INTEGER DEFAULT 1; """)
cur.execute("""ALTER TABLE orders ADD COLUMN created_at TEXT;""")
cur.execute("""CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER,
    item_id INTEGER,
    name TEXT,
    price REAL,
    quantity INTEGER
);""")

conn.commit()

conn.close()

print("Database created successfully")