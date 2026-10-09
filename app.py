#Billing counter - pick products (by piece or weight), customer number, cash / online payment, bill.

import re
import customtkinter as ctk
from tkinter import messagebox

import db
import invoice

SHOP_NAME = "My Shop"
SHOP_UPI = "yourshop@upi"      # put your real UPI id here

ACCENT, ACCENT_HOVER = "#2f80ed", "#1c63c4"
GREEN, RED = "#27ae60", "#e74c3c"
CAT_COLOR = {"Fruits & Veg": "#2ecc71", "Grocery": "#e67e22", "Dairy & Bakery": "#3498db", "Snacks": "#f1c40f",
             "Cold Drinks": "#1abc9c", "Cosmetics": "#e84393", "Household": "#9b59b6"}
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class WeightDialog(ctk.CTkToplevel):
    def __init__(self, parent, name, on_add):
        super().__init__(parent)
        _, mrp, _, disc, unit = db.PRODUCTS[name]
        self.sub, self.on_add, self.price = db.SUBUNIT[unit], on_add, db.unit_price(name)
        self.title(name)
        self.geometry("410x500")
        self.resizable(False, False)
        self.transient(parent)
        self.after(150, self.grab_set)
        ctk.CTkLabel(self, text=name, font=("Segoe UI", 24, "bold")).pack(pady=(22, 0))
        note = f"Rs. {self.price:.2f} per {unit}" + (f"   ({disc}% off, MRP {mrp:g})" if disc else "")
        ctk.CTkLabel(self, text=note, text_color="gray").pack()
        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(pady=18)
        self.amount = ctk.StringVar()
        for i, v in enumerate((250, 500, 750, 1000, 2000, 5000)):
            ctk.CTkButton(grid, text=db.qty_text(unit, v / 1000), width=104, height=42, fg_color="gray30",
                          command=lambda v=v: self.amount.set(str(v))).grid(row=i // 3, column=i % 3, padx=4, pady=4)
        ctk.CTkLabel(self, text=f"or type the weight in {self.sub}", text_color="gray").pack()
        e = ctk.CTkEntry(self, textvariable=self.amount, width=200, height=46, justify="center", font=("Segoe UI", 22))
        e.pack(pady=8)
        e.focus()
        e.bind("<Return>", lambda ev: self.add())
        self.amount.trace_add("write", self.update)
        self.cost = ctk.CTkLabel(self, text="Rs. 0.00", font=("Segoe UI", 32, "bold"), text_color=GREEN)
        self.cost.pack(pady=8)
        self.btn = ctk.CTkButton(self, text="Add to bill", height=48, state="disabled", command=self.add)
        self.btn.pack(fill="x", padx=30, pady=(4, 20))

    def qty(self):
        try:
            v = float(self.amount.get())
        except ValueError:
            return 0
        return round(v / 1000, 3) if 0 < v <= 50000 else 0

    def update(self, *_):
        q = self.qty()
        self.cost.configure(text=f"Rs. {q * self.price:,.2f}")
        self.btn.configure(state="normal" if q else "disabled")

    def add(self):
        q = self.qty()
        if q:
            self.destroy()
            self.on_add(q)


class PayDialog(ctk.CTkToplevel):
    def __init__(self, parent, bill_no, total, on_done):
        super().__init__(parent)
        self.title(f"Payment - Bill {bill_no}")
        self.geometry("430x640")
        self.resizable(False, False)
        self.transient(parent)
        self.after(150, self.grab_set)
        self.bill_no, self.total, self.on_done = bill_no, total, on_done
        self.mode = ctk.StringVar(value="Cash")
        ctk.CTkLabel(self, text="Amount to pay", text_color="gray").pack(pady=(22, 0))
        ctk.CTkLabel(self, text=f"Rs. {total:,.2f}", font=("Segoe UI", 36, "bold")).pack()
        ctk.CTkSegmentedButton(self, values=["Cash", "Online"], variable=self.mode,
                               command=self.switch).pack(pady=16)
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        self.switch("Cash")

    def switch(self, mode):
        for w in self.body.winfo_children():
            w.destroy()
        state = "normal"
        if mode == "Cash":
            self.given = ctk.StringVar()
            e = ctk.CTkEntry(self.body, textvariable=self.given, placeholder_text="Cash received",
                             height=44, width=230, justify="center", font=("Segoe UI", 20))
            e.pack(pady=(24, 10))
            e.focus()
            quick = ctk.CTkFrame(self.body, fg_color="transparent")
            quick.pack()
            ctk.CTkButton(quick, text="Exact", width=60, fg_color="gray35",
                          command=lambda: self.given.set(f"{self.total:.2f}")).pack(side="left", padx=3)
            for v in (100, 200, 500, 2000):
                ctk.CTkButton(quick, text=str(v), width=60, fg_color="gray35",
                              command=lambda v=v: self.given.set(str(v))).pack(side="left", padx=3)
            self.change = ctk.CTkLabel(self.body, text="Change to return: Rs. 0.00", font=("Segoe UI", 18, "bold"))
            self.change.pack(pady=22)
            self.given.trace_add("write", self.calc_change)
            state = "disabled"
        else:
            img = invoice.upi_qr(SHOP_UPI, SHOP_NAME, self.total, f"Bill {self.bill_no}")
            self.qr = ctk.CTkImage(light_image=img, size=(260, 260))
            ctk.CTkLabel(self.body, image=self.qr, text="").pack(pady=(4, 6))
            ctk.CTkLabel(self.body, text=f"Customer scans with GPay / PhonePe / Paytm\n{SHOP_UPI}",
                         text_color="gray").pack()
        self.ok = ctk.CTkButton(self.body, text="Payment received", height=46, state=state,
                                fg_color=GREEN, hover_color="#1e8449", command=self.finish)
        self.ok.pack(side="bottom", fill="x")

    def calc_change(self, *_):
        try:
            given = float(self.given.get())
        except ValueError:
            given = 0
        diff = given - self.total
        self.change.configure(text=f"Change to return: Rs. {max(diff, 0):,.2f}")
        self.ok.configure(state="normal" if given > 0 and diff >= 0 else "disabled")

    def finish(self):
        mode = "Cash" if self.mode.get() == "Cash" else "Online (UPI)"
        self.destroy()
        self.on_done(mode)


class BillingApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        db.init()
        self.title("Billing Counter")
        self.geometry("1360x780")
        self.minsize(1180, 700)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.cart = {}
        self.bill_no = ctk.IntVar(value=db.new_bill_no())
        self.search_var, self.cat_var = ctk.StringVar(), ctk.StringVar(value="All")
        self.name_var, self.phone_var = ctk.StringVar(), ctk.StringVar()
        self._build_sidebar()
        self.pages = {"bill": self._build_counter(), "history": self._build_history_page(),
                      "dash": self._build_dash_page()}
        self.phone_var.trace_add("write", self.phone_changed)
        self.show("bill")
        self.bind("<F2>", lambda e: self.checkout())
        self.bind("<Control-n>", lambda e: self.clear())
        self.after(300, self.search_entry.focus)

    def _build_sidebar(self):
        sb = ctk.CTkFrame(self, width=200, corner_radius=0)
        sb.grid(row=0, column=0, sticky="nsw")
        sb.grid_propagate(False)
        ctk.CTkLabel(sb, text=SHOP_NAME, font=("Segoe UI", 24, "bold")).pack(pady=(28, 4))
        ctk.CTkLabel(sb, text="Billing counter", text_color="gray").pack(pady=(0, 26))
        self.nav = {}
        for key, label in [("bill", "Billing Counter"), ("history", "Bill History"), ("dash", "Dashboard")]:
            b = ctk.CTkButton(sb, text=label, anchor="w", height=42, fg_color="transparent",
                              hover_color=("gray80", "gray25"), text_color=("gray10", "gray90"),
                              font=("Segoe UI", 15), command=lambda k=key: self.show(k))
            b.pack(fill="x", padx=14, pady=4)
            self.nav[key] = b
        sw = ctk.CTkSwitch(sb, text="Dark mode", command=self._toggle_theme)
        sw.pack(side="bottom", pady=20)
        sw.select()
        ctk.CTkButton(sb, text="Exit", fg_color="#c0392b", hover_color="#962d22",
                      command=self.destroy).pack(side="bottom", fill="x", padx=14)

    def _toggle_theme(self):
        ctk.set_appearance_mode("light" if ctk.get_appearance_mode() == "Dark" else "dark")

    def show(self, key):
        for p in self.pages.values():
            p.grid_forget()
        self.pages[key].grid(row=0, column=1, sticky="nsew", padx=18, pady=18)
        for k, b in self.nav.items():
            b.configure(fg_color=ACCENT if k == key else "transparent",
                        text_color="white" if k == key else ("gray10", "gray90"))
        if key == "history":
            self.refresh_history()
        elif key == "dash":
            self.refresh_dash()
        elif key == "bill":
            self.search_entry.focus()

    # ---------- counter ----------
    def _build_counter(self):
        page = ctk.CTkFrame(self, fg_color="transparent")
        page.grid_columnconfigure(0, weight=3)
        page.grid_columnconfigure(1, weight=2, minsize=450)
        page.grid_rowconfigure(2, weight=1)

        bar = ctk.CTkFrame(page, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=(0, 14))
        bar.grid_columnconfigure(0, weight=1)
        self.search_entry = ctk.CTkEntry(bar, textvariable=self.search_var, height=46, corner_radius=12,
                                         font=("Segoe UI", 15), placeholder_text="Search products  (rice, milk, apple...)")
        self.search_entry.grid(row=0, column=0, sticky="ew")
        self.toast = ctk.CTkLabel(bar, text="", text_color=GREEN, font=("Segoe UI", 14, "bold"))
        self.toast.grid(row=0, column=1, padx=14)

        chips = ctk.CTkScrollableFrame(page, orientation="horizontal", height=46, fg_color="transparent")
        chips.grid(row=1, column=0, sticky="ew", padx=(0, 14), pady=(8, 4))
        self.chips = {}
        for cat in ["All"] + list(db.CATALOG):
            c = ctk.CTkButton(chips, text=cat, height=34, corner_radius=17, width=20, font=("Segoe UI", 13, "bold"),
                              command=lambda x=cat: self.set_category(x))
            c.pack(side="left", padx=4)
            self.chips[cat] = c

        self.grid_box = ctk.CTkScrollableFrame(page, fg_color="transparent")
        self.grid_box.grid(row=2, column=0, sticky="nsew", padx=(0, 14))
        for col in range(3):
            self.grid_box.grid_columnconfigure(col, weight=1, uniform="prod")
        self.pbtn = {}
        for name, (cat, mrp, rate, disc, unit) in db.PRODUCTS.items():
            price = f"Rs. {db.unit_price(name):.2f}" + (f" / {unit}" if unit in db.SUBUNIT else "")
            tag = f"   |   {disc}% off" if disc else ""
            self.pbtn[name] = ctk.CTkButton(
                self.grid_box, text=f"{name}\n{price}{tag}", anchor="w", height=76, corner_radius=14,
                font=("Segoe UI", 14, "bold"), fg_color=("gray88", "gray19"), hover_color=("gray78", "gray28"),
                text_color=("gray10", "gray95"), border_width=2, border_color=CAT_COLOR.get(cat, "gray50"),
                command=lambda n=name: self.pick(n))
        self.empty_lbl = ctk.CTkLabel(self.grid_box, text="No product found", text_color="gray", font=("Segoe UI", 16))
        self.search_var.trace_add("write", lambda *a: self.filter_products())
        self.set_category("All")

        right = ctk.CTkFrame(page, corner_radius=16)
        right.grid(row=0, column=1, rowspan=3, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(3, weight=1)
        head = ctk.CTkFrame(right, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 6))
        head.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(head, text="Current Bill", font=("Segoe UI", 20, "bold")).grid(row=0, column=0, sticky="w")
        self.bill_lbl = ctk.CTkLabel(head, text="", text_color=ACCENT, font=("Segoe UI", 14, "bold"))
        self.bill_lbl.grid(row=0, column=1)
        cust = ctk.CTkFrame(right, fg_color="transparent")
        cust.grid(row=1, column=0, sticky="ew", padx=18)
        cust.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(cust, text="Customer Name", anchor="w", font=("Segoe UI", 13, "bold")
                     ).grid(row=0, column=0, sticky="w", padx=(2, 0))
        ctk.CTkLabel(cust, text="Phone No  *", anchor="w", font=("Segoe UI", 13, "bold")
                     ).grid(row=0, column=1, sticky="w", padx=(8, 0))
        ctk.CTkEntry(cust, textvariable=self.name_var, height=40, placeholder_text="Type name here"
                     ).grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=(2, 0))
        self.phone_entry = ctk.CTkEntry(cust, textvariable=self.phone_var, height=40,
                                        placeholder_text="10 digit number")
        self.phone_entry.grid(row=1, column=1, sticky="ew", padx=(6, 0), pady=(2, 0))
        self.entry_border = self.phone_entry.cget("border_color")
        ctk.CTkFrame(right, height=1, fg_color=("gray75", "gray30")).grid(row=2, column=0, sticky="ew", padx=18, pady=10)
        self.cart_box = ctk.CTkScrollableFrame(right, fg_color="transparent")
        self.cart_box.grid(row=3, column=0, sticky="nsew", padx=8)

        sumf = ctk.CTkFrame(right, fg_color=("gray90", "gray16"), corner_radius=12)
        sumf.grid(row=4, column=0, sticky="ew", padx=18, pady=12)
        sumf.grid_columnconfigure(1, weight=1)
        self.sum = {}
        for i, key in enumerate(["Items", "Total MRP", "Discount", "GST"]):
            ctk.CTkLabel(sumf, text=key, text_color="gray").grid(row=i, column=0, sticky="w", padx=14, pady=1)
            self.sum[key] = ctk.CTkLabel(sumf, text="-")
            self.sum[key].grid(row=i, column=1, sticky="e", padx=14)
        ctk.CTkLabel(sumf, text="TOTAL", font=("Segoe UI", 15, "bold")).grid(row=4, column=0, sticky="w", padx=14, pady=(8, 0))
        self.total_lbl = ctk.CTkLabel(sumf, text="Rs. 0.00", font=("Segoe UI", 32, "bold"), text_color=GREEN)
        self.total_lbl.grid(row=4, column=1, sticky="e", padx=14, pady=(8, 0))
        self.saved_lbl = ctk.CTkLabel(sumf, text="", text_color=GREEN)
        self.saved_lbl.grid(row=5, column=0, columnspan=2, pady=(0, 8))

        btns = ctk.CTkFrame(right, fg_color="transparent")
        btns.grid(row=5, column=0, sticky="ew", padx=18, pady=(0, 16))
        btns.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(btns, text="Cancel", width=90, height=52, fg_color="gray35", hover_color="gray25",
                      command=self.clear).grid(row=0, column=1, padx=(8, 0))
        ctk.CTkButton(btns, text="Proceed to Pay   (F2)", height=52, font=("Segoe UI", 17, "bold"),
                      fg_color=ACCENT, hover_color=ACCENT_HOVER, command=self.checkout).grid(row=0, column=0, sticky="ew")
        self.refresh()
        return page

    def set_category(self, cat):
        self.cat_var.set(cat)
        for k, c in self.chips.items():
            on = k == cat
            c.configure(fg_color=ACCENT if on else ("gray85", "gray25"),
                        hover_color=ACCENT_HOVER if on else ("gray75", "gray32"),
                        text_color="white" if on else ("gray10", "gray90"))
        self.filter_products()

    def filter_products(self):
        q, cat = self.search_var.get().strip().lower(), self.cat_var.get()
        self.empty_lbl.grid_forget()
        for b in self.pbtn.values():
            b.grid_forget()
        n = 0
        for name, b in self.pbtn.items():
            if (cat == "All" or db.PRODUCTS[name][0] == cat) and q in name.lower():
                b.grid(row=n // 3, column=n % 3, padx=5, pady=5, sticky="ew")
                n += 1
        if n == 0:
            self.empty_lbl.grid(row=0, column=0, columnspan=3, pady=60)

    def pick(self, name):
        if db.PRODUCTS[name][4] in db.SUBUNIT:
            WeightDialog(self, name, lambda q: self.add_item(name, q))
        else:
            self.add_item(name, 1)

    def add_item(self, name, qty=1):
        self.cart[name] = round(self.cart.get(name, 0) + qty, 3)
        self.toast.configure(text=f"+ {name}  {db.qty_text(db.PRODUCTS[name][4], qty)}")
        self.refresh()

    def step(self, name, d):
        unit = db.PRODUCTS[name][4]
        self.cart[name] = round(self.cart[name] + d * (0.25 if unit in db.SUBUNIT else 1), 3)
        if self.cart[name] <= 0:
            del self.cart[name]
        self.refresh()

    def remove(self, name):
        self.cart.pop(name, None)
        self.refresh()

    def refresh(self):
        calc = db.calculate(self.cart)
        for w in self.cart_box.winfo_children():
            w.destroy()
        if not calc["lines"]:
            ctk.CTkLabel(self.cart_box, text="Cart is empty\nTap a product to add it", text_color="gray",
                         font=("Segoe UI", 15)).pack(pady=50)
        for l in reversed(calc["lines"]):
            r = ctk.CTkFrame(self.cart_box, corner_radius=10, fg_color=("gray90", "gray19"))
            r.pack(fill="x", pady=3, padx=4)
            r.grid_columnconfigure(0, weight=1)
            per = f"/{l['unit']}" if l["unit"] in db.SUBUNIT else ""
            ctk.CTkLabel(r, text=l["name"], anchor="w", font=("Segoe UI", 14, "bold")).grid(row=0, column=0, sticky="w", padx=(12, 4), pady=(8, 0))
            sub = f"Rs. {l['price']:.2f}{per}" + (f"   ({l['disc']}% off)" if l["disc"] else "")
            ctk.CTkLabel(r, text=sub, anchor="w", text_color="gray", font=("Segoe UI", 12)).grid(row=1, column=0, sticky="w", padx=(12, 4), pady=(0, 8))
            q = ctk.CTkFrame(r, fg_color="transparent")
            q.grid(row=0, column=1, rowspan=2, padx=4)
            ctk.CTkButton(q, text="-", width=28, height=28, fg_color="gray35", command=lambda x=l["name"]: self.step(x, -1)).pack(side="left")
            ctk.CTkLabel(q, text=db.qty_text(l["unit"], l["qty"]), width=62, font=("Segoe UI", 13, "bold")).pack(side="left")
            ctk.CTkButton(q, text="+", width=28, height=28, fg_color="gray35", command=lambda x=l["name"]: self.step(x, 1)).pack(side="left")
            ctk.CTkLabel(r, text=f"{l['amount']:.2f}", width=76, anchor="e", font=("Segoe UI", 14, "bold")).grid(row=0, column=2, rowspan=2, padx=4)
            ctk.CTkButton(r, text="x", width=26, height=26, fg_color="transparent", text_color=RED, hover_color=("gray80", "gray28"),
                          command=lambda x=l["name"]: self.remove(x)).grid(row=0, column=3, rowspan=2, padx=(0, 8))
        self.bill_lbl.configure(text=f"Bill No: {self.bill_no.get()}")
        self.sum["Items"].configure(text=str(len(calc["lines"])))
        self.sum["Total MRP"].configure(text=f"Rs. {calc['mrp_total']:,.2f}")
        self.sum["Discount"].configure(text=f"- Rs. {calc['discount']:,.2f}")
        self.sum["GST"].configure(text=f"Rs. {calc['tax']:,.2f}")
        self.total_lbl.configure(text=f"Rs. {calc['total']:,.2f}")
        self.saved_lbl.configure(text=f"Customer saves Rs. {calc['discount']:,.2f}" if calc["discount"] > 0 else "")

    def phone_changed(self, *_):
        p = self.phone_var.get()
        digits = "".join(ch for ch in p if ch.isdigit())[:10]
        self.phone_entry.configure(border_color=self.entry_border)
        if digits != p:
            self.phone_var.set(digits)
            return
        if len(digits) == 10 and not self.name_var.get().strip():
            self.name_var.set(db.name_by_phone(digits))

    def checkout(self):
        calc = db.calculate(self.cart)
        if not calc["lines"]:
            return messagebox.showwarning("Empty bill", "Add at least one product first.")
        phone = self.phone_var.get().strip()
        if not re.fullmatch(r"\d{10}", phone):
            messagebox.showwarning("Phone No", "Enter the customer's 10 digit phone number.")
            self.phone_entry.configure(border_color=RED)
            self.phone_entry.focus()
            return
        name = self.name_var.get().strip() or "Customer"
        bid = self.bill_no.get()
        PayDialog(self, bid, calc["total"], lambda mode: self.finish_sale(bid, name, phone, calc, mode))

    def finish_sale(self, bid, name, phone, calc, mode):
        db.save_bill(bid, name, phone, calc, mode)
        path = invoice.make_pdf(db.get_bill(bid))
        if messagebox.askyesno("Payment done", f"Bill {bid} saved ({mode}).\nOpen the bill to print?"):
            invoice.open_file(path)
        self.clear()

    def clear(self):
        self.cart.clear()
        self.name_var.set("")
        self.phone_var.set("")
        self.bill_no.set(db.new_bill_no())
        self.toast.configure(text="")
        self.search_var.set("")
        self.set_category("All")
        self.refresh()
        self.search_entry.focus()

    # ---------- history ----------
    @staticmethod
    def _set_text(box, text):
        box.configure(state="normal")
        box.delete("1.0", "end")
        box.insert("1.0", text)
        box.configure(state="disabled")

    def _build_history_page(self):
        page = ctk.CTkFrame(self, fg_color="transparent")
        page.grid_columnconfigure((0, 1), weight=1)
        page.grid_rowconfigure(1, weight=1)
        self.q = ctk.StringVar()
        self.q.trace_add("write", lambda *a: self.refresh_history())
        ctk.CTkEntry(page, textvariable=self.q, height=40,
                     placeholder_text="Search by bill no, name or phone...").grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        self.hist_list = ctk.CTkScrollableFrame(page)
        self.hist_list.grid(row=1, column=0, sticky="nsew", padx=(0, 12))
        right = ctk.CTkFrame(page)
        right.grid(row=1, column=1, sticky="nsew")
        right.grid_rowconfigure(0, weight=1)
        right.grid_columnconfigure(0, weight=1)
        self.hist_view = ctk.CTkTextbox(right, font=("Consolas", 13), wrap="none", state="disabled")
        self.hist_view.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        self.hist_pdf = ctk.CTkButton(right, text="Open bill PDF", state="disabled", command=self._open_selected)
        self.hist_pdf.grid(row=1, column=0, pady=(0, 14))
        self.selected = None
        return page

    def refresh_history(self):
        for w in self.hist_list.winfo_children():
            w.destroy()
        for b in db.search(self.q.get()):
            ctk.CTkButton(self.hist_list, anchor="w", height=52, fg_color=("gray85", "gray20"),
                          hover_color=("gray75", "gray30"), text_color=("gray10", "gray95"),
                          text=f"#{b['id']}  {b['customer']}   -   Rs. {b['total']:,.2f}\n{b['created']}  |  {b['phone']}  |  {b['pay_mode'] or 'Cash'}",
                          command=lambda i=b["id"]: self.view_bill(i)).pack(fill="x", pady=3)

    def view_bill(self, bid):
        self.selected = db.get_bill(bid)
        self._set_text(self.hist_view, invoice.render_text(self.selected))
        self.hist_pdf.configure(state="normal")

    def _open_selected(self):
        if self.selected:
            invoice.open_file(invoice.make_pdf(self.selected))

    # ---------- dashboard ----------
    def _build_dash_page(self):
        page = ctk.CTkFrame(self, fg_color="transparent")
        page.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.cards = []
        for i, title in enumerate(["Today's Sales", "Today's Bills", "Total Revenue", "Total Bills"]):
            c = ctk.CTkFrame(page)
            c.grid(row=0, column=i, sticky="ew", padx=6, pady=6)
            ctk.CTkLabel(c, text=title, text_color="gray").pack(pady=(14, 0))
            v = ctk.CTkLabel(c, text="-", font=("Segoe UI", 26, "bold"))
            v.pack(pady=(0, 14))
            self.cards.append(v)
        self.top_box = ctk.CTkFrame(page)
        self.top_box.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=6, pady=6)
        self.cat_box = ctk.CTkFrame(page)
        self.cat_box.grid(row=1, column=2, columnspan=2, sticky="nsew", padx=6, pady=6)
        return page

    def refresh_dash(self):
        s = db.stats()
        for lbl, val in zip(self.cards, [f"Rs. {s['today_s']:,.0f}", s["today_n"], f"Rs. {s['all_s']:,.0f}", s["all_n"]]):
            lbl.configure(text=str(val))
        self._bars(self.top_box, "Top Selling Items (Rs.)", s["top"])
        self._bars(self.cat_box, "Revenue by Category (Rs.)", s["cats"])

    @staticmethod
    def _bars(box, title, data):
        for w in box.winfo_children():
            w.destroy()
        ctk.CTkLabel(box, text=title, font=("Segoe UI", 16, "bold")).pack(pady=(14, 8))
        mx = max([v for _, v in data], default=1) or 1
        for name, v in data:
            r = ctk.CTkFrame(box, fg_color="transparent")
            r.pack(fill="x", padx=16, pady=4)
            ctk.CTkLabel(r, text=name, width=110, anchor="w").pack(side="left")
            bar = ctk.CTkProgressBar(r)
            bar.set(v / mx)
            bar.pack(side="left", fill="x", expand=True, padx=8)
            ctk.CTkLabel(r, text=f"{v:,.0f}", width=70, anchor="e").pack(side="left")
        if not data:
            ctk.CTkLabel(box, text="No data yet", text_color="gray").pack(pady=30)


if __name__ == "__main__":
    BillingApp().mainloop()
