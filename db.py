#Product catalog, pricing rules and SQLite storage.

import random
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).with_name("billing.db")

# category -> (GST rate, [(product, MRP, discount %, unit)])
# unit "kg" / "L" = sold loose by weight or volume, MRP is per kg / per litre; "pc" = per piece or pack
CATALOG = {
    "Fruits & Veg": (0.0, [
        ("Potato", 30, 0, "kg"), ("Onion", 40, 5, "kg"), ("Tomato", 50, 0, "kg"), ("Carrot", 60, 0, "kg"),
        ("Cabbage", 35, 0, "kg"), ("Cauliflower", 45, 0, "kg"), ("Spinach", 40, 0, "kg"),
        ("Apple", 180, 10, "kg"), ("Banana", 60, 0, "kg"), ("Mango", 120, 5, "kg"), ("Orange", 80, 0, "kg"),
        ("Grapes", 100, 8, "kg"), ("Lemon", 6, 0, "pc"), ("Coriander Bunch", 10, 0, "pc")]),
    "Grocery": (0.10, [
        ("Rice", 80, 5, "kg"), ("Daal", 60, 0, "kg"), ("Sugar", 45, 0, "kg"), ("Salt", 25, 0, "kg"),
        ("Besan", 90, 5, "kg"), ("Poha", 60, 0, "kg"), ("Food Oil", 180, 8, "L"), ("Mustard Oil", 190, 5, "L"),
        ("Wheat Atta (5 kg)", 240, 10, "pc"), ("Tea (250 g)", 150, 12, "pc"), ("Coffee (100 g)", 240, 10, "pc"),
        ("Turmeric (100 g)", 35, 0, "pc"), ("Red Chilli (100 g)", 45, 0, "pc")]),
    "Dairy & Bakery": (0.05, [
        ("Milk", 60, 0, "L"), ("Paneer", 360, 5, "kg"), ("Curd (400 g)", 40, 0, "pc"),
        ("Butter (100 g)", 58, 0, "pc"), ("Cheese Slices", 120, 8, "pc"), ("Bread", 40, 0, "pc"),
        ("Eggs (dozen)", 84, 0, "pc"), ("Cake Rusk", 50, 0, "pc")]),
    "Snacks": (0.12, [
        ("Chips", 20, 0, "pc"), ("Biscuits", 30, 5, "pc"), ("Chocolate", 50, 10, "pc"),
        ("Instant Noodles", 14, 0, "pc"), ("Cookies", 80, 10, "pc"), ("Namkeen (loose)", 220, 0, "kg"),
        ("Peanuts", 140, 0, "kg"), ("Dry Fruits Mix", 800, 5, "kg")]),
    "Cold Drinks": (0.05, [
        ("Mazza", 60, 10, "pc"), ("Coke", 60, 0, "pc"), ("Frooti", 50, 5, "pc"), ("Thumbs Up", 45, 0, "pc"),
        ("Limca", 40, 0, "pc"), ("Sprite", 60, 10, "pc"), ("Pepsi", 60, 0, "pc"), ("Fanta", 60, 5, "pc"),
        ("Water Bottle (1 L)", 20, 0, "pc"), ("Fruit Juice (1 L)", 110, 10, "pc"), ("Energy Drink", 110, 0, "pc")]),
    "Cosmetics": (0.05, [
        ("Bath Soap", 40, 10, "pc"), ("Face Cream", 120, 15, "pc"), ("Face Wash", 60, 0, "pc"),
        ("Hair Spray", 180, 20, "pc"), ("Hair Gel", 140, 10, "pc"), ("Body Lotion", 180, 5, "pc"),
        ("Shampoo", 180, 15, "pc"), ("Tooth Paste", 90, 10, "pc"), ("Deodorant", 220, 20, "pc"),
        ("Talcum Powder", 110, 0, "pc"), ("Hand Wash", 75, 5, "pc")]),
    "Household": (0.18, [
        ("Detergent Powder (1 kg)", 120, 10, "pc"), ("Dish Wash Gel", 90, 5, "pc"),
        ("Floor Cleaner", 160, 15, "pc"), ("Tissue Paper", 40, 0, "pc"), ("Garbage Bags", 60, 0, "pc"),
        ("Phenyl", 70, 0, "pc")]),
}
PRODUCTS = {n: (cat, mrp, rate, disc, unit)
            for cat, (rate, items) in CATALOG.items() for n, mrp, disc, unit in items}
SUBUNIT = {"kg": "g", "L": "ml"}


def unit_price(name: str) -> float:
    mrp, disc = PRODUCTS[name][1], PRODUCTS[name][3]
    return round(mrp * (100 - disc) / 100, 2)


def qty_text(unit: str, qty: float) -> str:
    if unit in SUBUNIT:
        return f"{round(qty * 1000)} {SUBUNIT[unit]}" if qty < 1 else f"{qty:g} {unit}"
    return f"{qty:g}"


def rate_text(mrp: float, unit: str) -> str:
    return f"{mrp:g}/{unit}" if unit in SUBUNIT else f"{mrp:g}"


def calculate(cart: dict) -> dict:
    lines, by_cat, mrp_total, subtotal = [], {}, 0.0, 0.0
    for name, qty in cart.items():
        if qty <= 0:
            continue
        cat, mrp, rate, disc, unit = PRODUCTS[name]
        unit_p = unit_price(name)
        amount = round(unit_p * qty, 2)
        lines.append({"name": name, "category": cat, "qty": qty, "unit": unit, "mrp": mrp, "disc": disc,
                      "price": unit_p, "amount": amount})
        mrp_total += mrp * qty
        subtotal += amount
        by_cat[cat] = by_cat.get(cat, 0) + amount
    tax_by_cat = {c: round(a * CATALOG[c][0], 2) for c, a in by_cat.items()}
    tax = round(sum(tax_by_cat.values()), 2)
    subtotal = round(subtotal, 2)
    return {"lines": lines, "mrp_total": round(mrp_total, 2), "discount": round(mrp_total - subtotal, 2),
            "subtotal": subtotal, "tax_by_cat": tax_by_cat, "tax": tax, "total": round(subtotal + tax, 2)}


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init():
    with _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS bills(
            id INTEGER PRIMARY KEY AUTOINCREMENT, customer TEXT NOT NULL, phone TEXT NOT NULL,
            subtotal REAL, tax REAL, total REAL, created TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS items(
            bill_id INTEGER REFERENCES bills(id), name TEXT, category TEXT,
            qty INTEGER, price REAL, amount REAL, mrp REAL);
        """)
        if "pay_mode" not in [r["name"] for r in c.execute("PRAGMA table_info(bills)")]:
            c.execute("ALTER TABLE bills ADD COLUMN pay_mode TEXT DEFAULT 'Cash'")
        if "mrp" not in [r["name"] for r in c.execute("PRAGMA table_info(items)")]:
            c.execute("ALTER TABLE items ADD COLUMN mrp REAL")


def new_bill_no() -> int:
    with _conn() as c:
        while True:
            no = random.randint(100000, 999999)
            if not c.execute("SELECT 1 FROM bills WHERE id=?", (no,)).fetchone():
                return no


def name_by_phone(phone: str) -> str:
    with _conn() as c:
        r = c.execute("SELECT customer FROM bills WHERE phone=? ORDER BY id DESC LIMIT 1", (phone,)).fetchone()
    return r["customer"] if r else ""


def save_bill(bill_no: int, customer: str, phone: str, calc: dict, pay_mode: str = "Cash") -> int:
    with _conn() as c:
        c.execute("INSERT INTO bills(id,customer,phone,subtotal,tax,total,created,pay_mode) VALUES(?,?,?,?,?,?,?,?)",
                  (bill_no, customer, phone, calc["subtotal"], calc["tax"], calc["total"],
                   datetime.now().strftime("%Y-%m-%d %H:%M"), pay_mode))
        c.executemany("INSERT INTO items VALUES(?,?,?,?,?,?,?)",
                      [(bill_no, l["name"], l["category"], l["qty"], l["price"], l["amount"], l["mrp"])
                       for l in calc["lines"]])
    return bill_no


def get_bill(bid: int):
    with _conn() as c:
        b = c.execute("SELECT * FROM bills WHERE id=?", (bid,)).fetchone()
        if not b:
            return None
        rows = [dict(r) for r in c.execute("SELECT * FROM items WHERE bill_id=?", (bid,))]
    lines, tax_by_cat, mrp_total = [], {}, 0.0
    for l in rows:
        l["mrp"] = l["mrp"] or l["price"]
        l["unit"] = PRODUCTS[l["name"]][4] if l["name"] in PRODUCTS else "pc"
        l["disc"] = round((l["mrp"] - l["price"]) / l["mrp"] * 100) if l["mrp"] else 0
        mrp_total += l["mrp"] * l["qty"]
        rate = CATALOG.get(l["category"], (0,))[0]
        tax_by_cat[l["category"]] = tax_by_cat.get(l["category"], 0) + l["amount"] * rate
        lines.append(l)
    tax_by_cat = {k: round(v, 2) for k, v in tax_by_cat.items()}
    return {**dict(b), "lines": lines, "tax_by_cat": tax_by_cat, "mrp_total": mrp_total,
            "discount": round(mrp_total - b["subtotal"], 2)}


def search(q: str = "", limit: int = 100):
    like = f"%{q.strip()}%"
    with _conn() as c:
        rows = c.execute("SELECT * FROM bills WHERE CAST(id AS TEXT) LIKE ? OR customer LIKE ? OR phone LIKE ? "
                         "ORDER BY created DESC, id DESC LIMIT ?", (like, like, like, limit)).fetchall()
    return [dict(r) for r in rows]


def stats() -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    with _conn() as c:
        t = c.execute("SELECT COUNT(*) n, COALESCE(SUM(total),0) s FROM bills WHERE created LIKE ?", (today + "%",)).fetchone()
        a = c.execute("SELECT COUNT(*) n, COALESCE(SUM(total),0) s FROM bills").fetchone()
        top = c.execute("SELECT name, SUM(amount) q FROM items GROUP BY name ORDER BY q DESC LIMIT 5").fetchall()
        cats = c.execute("SELECT category, SUM(amount) s FROM items GROUP BY category ORDER BY s DESC").fetchall()
    return {"today_n": t["n"], "today_s": t["s"], "all_n": a["n"], "all_s": a["s"],
            "top": [(r["name"], r["q"]) for r in top], "cats": [(r["category"], r["s"]) for r in cats]}
