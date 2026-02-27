import requests
import time
from escpos.printer import Win32Raw
from datetime import datetime

# --- SOZLAMALAR ---
# Django API manzili
BACKEND_URL = "https://xoztovar.api.ardentsoft.uz/api/print"
PRINTER_NAME = "POS58B"  # Printer nomi
WIDTH = 32

def line(char='-'):
    return char * WIDTH + "\n"

def lr(left, right):
    """Chap va O'ng matnni joylash"""
    left = str(left).strip()
    right = str(right).strip()
    space = WIDTH - len(left) - len(right)
    if space < 1:
        left = left[: max(0, WIDTH - len(right) - 1)]
        space = WIDTH - len(left) - len(right)
        if space < 1: space = 1
    return left + (" " * space) + right + "\n"

def money(amount):
    return f"{amount:,}".replace(",", " ")

def test_printer():
    """Start oldidan printerni tekshirish"""
    try:
        print(f"🖨️ Printerga ulanish: {PRINTER_NAME}...")
        p = Win32Raw(PRINTER_NAME)
        p.text("Agent ishga tushdi!\n\n")
        print("✅ Printer OK! Sinov yozuvi chiqishi kerak.")
        return True
    except Exception as e:
        print(f"❌ Printer Xatosi: {e}")
        print("💡 Maslahat: Printer nomi to'g'riligini va USB ulanganini tekshiring.")
        return False

def print_receipt(job_data):
    try:
        p = Win32Raw(PRINTER_NAME)
    except Exception as e:
        print(f"❌ Printer xatosi: {e}")
        return False, str(e)

    try:
        print(f"🖨️ Chop etilmoqda: Job ID {job_data.get('check_id', '?')}")
        
        # Init
        p._raw(b"\x1b\x40")          # Init
        p._raw(b"\x1b\x74\x11")      # Set char table to WPC1251 if needed
        
        # Header - STROYCRM
        p._raw(b"\x1b\x61\x01")      # Center
        p._raw(b"\x1b\x45\x01")      # Bold On
        p._raw(b"\x1d\x21\x11")      # Double Size (Width & Height)
        p.text("STROYCRM\n")
        
        # Subtitle
        p._raw(b"\x1d\x21\x00")      # Normal Size
        p._raw(b"\x1b\x45\x00")      # Bold Off
        p.text("QURILISH MOLLARI DO'KONI\n\n")
        
        # Info block
        p._raw(b"\x1b\x61\x00")      # Left align
        cashier = job_data.get('cashier', 'admin')
        customer = job_data.get('customer') or 'Umumiy mijoz'
        p.text(f"SOTUVCHI: {cashier}\n")
        p.text(f"MIJOZ: {customer}\n")
        
        p.text(line('.'))            # Dotted separator
        
        date_str = job_data.get('date', datetime.now().strftime("%d.%m.%Y"))
        
        p.text(f"SANA: {date_str}\n")
        p.text(f"CHEK " + chr(252) + f": {job_data.get('check_id', '-')}\n\n") # chr(252) => '№' symbol approximation if standard encoding or just print Number symbol string. fallback: No:
        
        # Table Header
        p._raw(b"\x1b\x45\x01")      # Bold On
        header = "MAHSULOT"
        header += " " * (WIDTH - len("MAHSULOT") - len("SONI") - len("SUMMA") - 2)
        header += " SONI SUMMA"
        p.text(header + "\n")
        p._raw(b"\x1b\x45\x00")      # Bold Off
        
        # Items
        for item in job_data.get('items', []):
            name = item.get('name') or item.get('product_name') or item.get('title') or "Mahsulot"
            quantity = float(item.get('quantity', 1))
            total = float(item.get('total', 0))
            
            # Formatting line variables
            qty_str = str(int(quantity) if quantity.is_integer() else quantity)
            total_str = money(total) + " so'm"
            
            # Print product name first
            # Truncate or fit name
            if len(name) > WIDTH:
                p.text(f"{name[:WIDTH]}\n")
            else:
                p.text(f"{name}\n")
            
            # Under it, we print quantity and total right aligned
            # E.g: "               1      45 000 so'm"
            space_middle = WIDTH - len(qty_str) - len(total_str) - 2
            if space_middle < 1: space_middle = 1
            
            calc_line = (" " * (WIDTH - space_middle - len(qty_str) - len(total_str))) + qty_str + (" " * space_middle) + total_str
            # Try to push exact to right
            calc_line = (" " * max(0, WIDTH - len(qty_str) - len(total_str) - 4)) + qty_str + "    " + total_str
            
            p.text(calc_line.rjust(WIDTH) + "\n")
            
        p.text(line('-'))
        p._raw(b"\x1b\x45\x01")      # Bold On
        p.text(line('-'))            # Double Line for grand totals
        
        # Grand Total
        subtotal_str = f"{money(job_data.get('total_amount', 0))} so'm"
        p._raw(b"\x1d\x21\x01")      # Double Height
        space = WIDTH - len("JAMI:") - len(subtotal_str)
        p.text(f"JAMI:{" " * max(1, space)}{subtotal_str}\n")
        p._raw(b"\x1d\x21\x00")      # Normal Height
        p._raw(b"\x1b\x45\x00")      # Bold Off
        
        p.text("\n")
        p.text(line('-'))            # Dashed Separator
        
        # Footer Message
        p._raw(b"\x1b\x61\x01")      # Center
        p._raw(b"\x1b\x45\x01")      # Bold On
        p._raw(b"\x1b\x4d\x01")      # Small Font? if supported.
        p.text("\nXaridingiz uchun rahmat!\n\n")
        
        p.text("Aloqa:\n")
        p._raw(b"\x1b\x45\x00")      # Bold Off
        p.text("+998 90 078 08 00\n")
        p.text("+998 88 856 13 33\n\n")
        
        p.text(line('-'))
        
        p._raw(b"\x1b\x45\x01")
        p.text("STROY CRM TIZIMI\n")
        p._raw(b"\x1b\x45\x00")
        p.text("www.ardentsoft.uz\n")
        p.text("+998 90 557 75 11\n")
        
        p.text("\n\n\n\n")
        
        # Cut
        p._raw(b"\x1d\x56\x00")
        p.close()
        
        print("✅ Muvaffaqiyatli chop etildi!")
        return True, None

    except Exception as e:
        print(f"❌ Chop etish jarayonida xatolik: {e}")
        return False, str(e)

def main():
    print(f"🚀 Agent ishga tushdi...")
    print(f"📡 Backend: {BACKEND_URL}")
    
    # Start Test
    if not test_printer():
        print("⚠️ Printer ishlamadi, lekin davom etamiz...")

    print("⏳ Kutish rejimi...")
    
    while True:
        try:
            # 1. Yangi vazifa bormi?
            resp = requests.get(f"{BACKEND_URL}/poll/", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                job_wrapper = data.get('job')
                
                if job_wrapper:
                    job_id = job_wrapper['id']
                    job_data = job_wrapper['data']
                    print(f"📥 Yangi vazifa qabul qilindi: {job_id}")
                    
                    # 2. Chop etish
                    success, error_msg = print_receipt(job_data)
                    
                    # 3. Tasdiqlash yoki xato qilish
                    if success:
                        ack_resp = requests.post(f"{BACKEND_URL}/ack/{job_id}/")
                        if ack_resp.status_code == 200:
                            print(f"✅ Vazifa {job_id} muvaffaqiyatli yakunlandi")
                    else:
                        print("⚠️ Vazifa bajarilmadi, serverga xatolik haqida xabar beramiz...")
                        requests.post(f"{BACKEND_URL}/fail/{job_id}/", json={"error": error_msg})
                    
                else:
                    # Vazifa yo'q, jim turamiz (har 2 soniyada so'raydi)
                    time.sleep(2)
            else:
                print(f"⚠️ Server javobi g'alati: {resp.status_code} - {resp.text}")
                time.sleep(5)
                
        except requests.exceptions.ConnectionError:
            print("❌ Serverga ulanib bo'lmadi (Backend ishlayaptimi?). Qayta urinish...")
            time.sleep(5)
        except Exception as e:
            print(f"❌ Kutilmagan xato: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
