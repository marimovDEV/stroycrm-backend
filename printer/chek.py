from escpos.printer import Win32Raw
from datetime import datetime

# 🔥 Bu yerga Windows'dagi printer nomini yozing:
# masalan: "POS58B" yoki "Generic / Text Only"
PRINTER_NAME = "POS58B"

# 58mm chek printerlar odatda 32 (yoki 42/48) ta belgiga sig'adi.
# Katta shriftda esa 2 barobar kam sig'adi.
WIDTH = 32

def line(char='-'):
    """To'liq chiziq tortish"""
    return char * WIDTH + "\n"

def lr(left: str, right: str):
    """
    Left-Right: chapda nom, o'ngda summa.
    Matn uzunligini hisobga olib joylashtiradi.
    """
    left = left.strip()
    right = right.strip()
    
    # O'ng tomondagi narx sig'ishi uchun joy hisoblash
    space_needed = WIDTH - len(left) - len(right)
    
    if space_needed < 1:
        # Agar sig'masa, chap tomonni qisqartiramiz (yoki keyingi qatorga tushirish mumkin)
        max_len = max(0, WIDTH - len(right) - 1)
        left = left[:max_len]
        space_needed = WIDTH - len(left) - len(right)
        if space_needed < 1:
            space_needed = 1
            
    return left + (" " * space_needed) + right + "\n"

def money_uzs(amount: int):
    """Summani chiroyli formatlash: 12 500 so'm"""
    return f"{amount:,}".replace(",", " ") + " so'm"

def print_receipt():
    try:
        p = Win32Raw(PRINTER_NAME)
    except Exception as e:
        print(f"Xatolik: Printer topilmadi ({e})")
        return

    shop_name = "TASTE RADAR"
    address_1 = "Toshkent shahri"
    address_2 = "Chilonzor tumani"

    stol = 9
    now = datetime.now()
    # Vaqtni chiroyli ko'rsatish
    sana_vaqt = now.strftime("%d.%m.%Y %H:%M")

    items = [
        ("Lager (3x)", 15750),
        ("Go'shtli pirog", 13500),
        ("Baliq va chips", 14950),
        ("Aralash gril", 18250),
        ("Qizil vino (2x)", 14000),
        ("Desert", 7950)
    ]

    subtotal = sum(x[1] for x in items)
    qqs_rate = 0.12
    qqs = int(round(subtotal * qqs_rate))
    total = subtotal + qqs

    # ======== START PRINT ========
    p._raw(b"\x1b\x40")          # Initialize

    # --- Header (Do'kon nomi) ---
    p._raw(b"\x1b\x61\x01")      # Center align
    p._raw(b"\x1d\x21\x11")      # Double width & height
    # Eslatma: Katta shriftda hardware centering ishlatganda manual bo'sh joy qo'shmaslik kerak!
    p.text(shop_name + "\n")     
    p._raw(b"\x1d\x21\x00")      # Normal size
    
    # Manzil va ma'lumotlar
    p.text(address_1 + "\n")
    p.text(address_2 + "\n")
    p.text(line('='))            # Chiroyli ajratgich
    
    # --- Check Info ---
    p._raw(b"\x1b\x45\x01")      # Bold ON
    p.text(f"STOL: {stol}  |  CHEK #1234\n")
    p._raw(b"\x1b\x45\x00")      # Bold OFF
    p.text(sana_vaqt + "\n")
    p.text(line('-'))

    # --- Items List ---
    p._raw(b"\x1b\x61\x00")      # Left align (mahsulotlar ro'yxati uchun)
    
    for name, price in items:
        p.text(lr(name, money_uzs(price)))

    p.text(line('-'))

    # --- Totals ---
    p.text(lr("Jami (QQSsiz):", money_uzs(subtotal)))
    p.text(lr(f"QQS ({int(qqs_rate*100)}%):", money_uzs(qqs)))
    
    p.text(line('='))
    
    # --- Grand Total ---
    p._raw(b"\x1b\x61\x01")      # Center align
    p._raw(b"\x1b\x45\x01")      # Bold ON
    p._raw(b"\x1d\x21\x01")      # Double Height only (sig'ishi osonroq bo'lishi uchun)
    p.text(f"JAMI: {money_uzs(total)}\n")
    p._raw(b"\x1d\x21\x00")      # Normal
    p._raw(b"\x1b\x45\x00")      # Bold OFF
    
    # --- Footer ---
    p.text("\n")
    p.text("Xaridingiz uchun rahmat!\n")
    p.text("Yana kutib qolamiz :)\n")
    p.text("www.tasteradar.uz\n")
    p.text("\n\n")

    # Cut Paper
    p._raw(b"\x1d\x56\x00")

if __name__ == "__main__":
    print_receipt()
