#Receipt text, PDF invoice and UPI QR.

import os
import subprocess
import sys
from pathlib import Path

from PIL import Image
from reportlab.graphics.barcode import qrencoder
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

BILLS_DIR = Path(__file__).with_name("bills")
import db

SHOP = "Our Shop"
W = 46


def render_text(bill: dict) -> str:
    row = lambda label, val: f"{label:<36}{val:>10.2f}"
    out = [SHOP.center(W), "=" * W,
           f"Bill No : {bill.get('id', '-')}", f"Name    : {bill.get('customer', '')}",
           f"Phone   : {bill.get('phone', '')}", f"Payment : {bill.get('pay_mode', '-')}",
           f"Date    : {bill.get('created', '')}", "=" * W,
           f"{'Item':<14}{'Qty':>8}{'MRP':>8}{'Disc':>6}{'Amount':>10}", "-" * W]
    for l in bill["lines"]:
        out.append(f"{l['name'][:14]:<14}{db.qty_text(l['unit'], l['qty']):>8}{db.rate_text(l['mrp'], l['unit']):>8}"
                   f"{str(l['disc']) + '%':>6}{l['amount']:>10.2f}")
    out += ["-" * W, row("Total MRP", bill["mrp_total"]), row("Discount", -bill["discount"]),
            row("Subtotal", bill["subtotal"])]
    for cat, t in bill["tax_by_cat"].items():
        out.append(row(f"GST - {cat}", t))
    out += ["=" * W, row("TOTAL (Rs.)", bill["total"]), "=" * W]
    if bill["discount"] > 0:
        out.append(f"You saved Rs. {bill['discount']:.2f}".center(W))
    out.append("Thank you! Visit again.".center(W))
    return "\n".join(out)


def make_pdf(bill: dict) -> Path:
    BILLS_DIR.mkdir(exist_ok=True)
    path = BILLS_DIR / f"bill_{bill['id']}.pdf"
    ss = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm)
    navy = colors.HexColor("#0f2a43")
    rows = [["Item", "Qty", "MRP", "Disc", "Price", "Amount"]]
    for l in bill["lines"]:
        rows.append([l["name"], db.qty_text(l["unit"], l["qty"]), db.rate_text(l["mrp"], l["unit"]), f"{l['disc']}%",
                     f"{l['price']:.2f}", f"{l['amount']:.2f}"])
    n = len(rows)
    rows.append(["", "", "", "", "Total MRP", f"{bill['mrp_total']:.2f}"])
    rows.append(["", "", "", "", "Discount", f"-{bill['discount']:.2f}"])
    rows.append(["", "", "", "", "Subtotal", f"{bill['subtotal']:.2f}"])
    rows += [["", "", "", "", f"GST {c}", f"{t:.2f}"] for c, t in bill["tax_by_cat"].items()]
    rows.append(["", "", "", "", "TOTAL (Rs.)", f"{bill['total']:.2f}"])
    t = Table(rows, colWidths=[52 * mm, 20 * mm, 24 * mm, 16 * mm, 26 * mm, 32 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), navy), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"), ("LINEBELOW", (0, 1), (-1, n - 1), 0.25, colors.lightgrey),
        ("ROWBACKGROUNDS", (0, 1), (-1, n - 1), [colors.white, colors.HexColor("#f3f6fa")]),
        ("LINEABOVE", (4, n), (-1, n), 0.8, navy), ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (4, -1), (-1, -1), colors.HexColor("#e1ecf7")),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    story = [Paragraph(f"<b>{SHOP}</b> - Invoice", ss["Title"]),
             Paragraph(f"Bill No: <b>{bill['id']}</b> &nbsp;&nbsp; Date: {bill.get('created', '')}", ss["Normal"]),
             Paragraph(f"Customer: {bill['customer']} &nbsp;&nbsp; Phone: {bill['phone']} &nbsp;&nbsp; "
                       f"Paid via: {bill.get('pay_mode', '-')}", ss["Normal"]),
             Spacer(1, 8 * mm), t, Spacer(1, 8 * mm)]
    if bill["discount"] > 0:
        story.append(Paragraph(f"<b>You saved Rs. {bill['discount']:.2f} on this bill!</b>", ss["Normal"]))
    story += [Spacer(1, 6 * mm), Paragraph("Thank you for shopping with us!", ss["Italic"])]
    doc.build(story)
    return path


def upi_qr(upi_id, payee, amount, note, scale=7):
    link = f"upi://pay?pa={upi_id}&pn={payee.replace(' ', '%20')}&am={amount:.2f}&cu=INR&tn={note.replace(' ', '%20')}"
    qr = qrencoder.QRCode(None, qrencoder.QRErrorCorrectLevel.M)
    qr.addData(link)
    qr.make()
    n = qr.getModuleCount()
    img = Image.new("RGB", (n + 8, n + 8), "white")
    for r in range(n):
        for c in range(n):
            if qr.isDark(r, c):
                img.putpixel((c + 4, r + 4), (0, 0, 0))
    return img.resize(((n + 8) * scale,) * 2, Image.NEAREST)


def open_file(path):
    if sys.platform.startswith("win"):
        os.startfile(path)
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(path)])
