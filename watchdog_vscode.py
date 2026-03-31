import pyautogui, pygetwindow as gw, numpy as np
import requests, time, keyboard, threading
from PIL import ImageGrab

TOKEN   = "8284714119:AAF6eSF-qpAAiTJnmIMHl_HTUd7zTRGapQI"
CHAT_ID = "7558816227"

# Màu banner vàng limit (lấy từ ảnh)
BANNER_COLOR_RGB = (180, 155, 90)
COLOR_TOLERANCE  = 45

# ── Telegram ──────────────────────────────────────────────

def tg(msg):
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                  json={"chat_id": CHAT_ID, "text": msg})

def wait_retry():
    tg("⚠️ Claude sắp/đã bị limit!\n\nGõ /retry khi muốn tiếp tục...")
    offset = None
    while True:
        r = requests.get(
            f"https://api.telegram.org/bot{TOKEN}/getUpdates",
            params={"offset": offset, "timeout": 30}
        ).json()
        for u in r.get("result", []):
            offset = u["update_id"] + 1
            if u.get("message", {}).get("text") == "/retry":
                tg("▶️ Đang retry...")
                type_continue()
                return
        time.sleep(2)

# ── VS Code ───────────────────────────────────────────────

def focus_vscode():
    import win32gui, win32con, win32process, win32api, ctypes

    hwnds = []
    win32gui.EnumWindows(
        lambda hwnd, r: r.append(hwnd) if "Visual Studio Code" in win32gui.GetWindowText(hwnd) else None,
        hwnds
    )
    if not hwnds:
        tg("❌ Không tìm thấy cửa sổ VS Code!")
        return False
    hwnd = hwnds[0]

    # 1) Nếu cửa sổ đang minimized, restore trước
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        time.sleep(0.5)

    # 2) Dùng keybd_event giả lập nhấn Alt để unlock foreground
    ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)        # Alt down
    ctypes.windll.user32.keybd_event(0x12, 0, 0x0002, 0)   # Alt up
    time.sleep(0.1)

    # 3) Thử SetForegroundWindow
    try:
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        # 4) Fallback: BringWindowToTop + ShowWindow
        try:
            win32gui.BringWindowToTop(hwnd)
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
        except Exception:
            pass

    time.sleep(1.5)

    # Kiểm tra xem đã focus chưa
    if win32gui.GetForegroundWindow() != hwnd:
        tg("⚠️ Không focus được VS Code, thử Alt+Tab thủ công")
        return False

    return True

def find_send_button():
    """Tìm nút ↑ trên màn hình"""
    try:
        loc = pyautogui.locateOnScreen("send_button.png", confidence=0.6)
        if loc:
            return pyautogui.center(loc)
    except Exception as e:
        print(f"[!] Không tìm thấy nút ↑: {e}")
    return None

def type_continue():
    if not focus_vscode():
        return

    pos = find_send_button()
    if not pos:
        tg("❌ Không tìm thấy nút ↑ — thử lại sau")
        return

    btn_x, btn_y = pos

    # Input box = hàng trên nút ↑, dịch sang trái vào giữa
    input_x = btn_x - 400
    input_y = btn_y - 45

    # Click vào input, xóa text cũ, gõ continue
    pyautogui.click(input_x, input_y)
    time.sleep(0.3)
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.1)
    pyautogui.typewrite("continue", interval=0.05)
    time.sleep(0.2)

    # Bấm Enter để gửi (đơn giản hơn click nút ↑)
    pyautogui.press("enter")
    tg("✅ Đã gõ continue vào Claude!")

# ── Detect banner ─────────────────────────────────────────

def has_limit_banner():
    """Chụp 1/5 trên màn hình, đếm pixel màu vàng của banner"""
    screen = ImageGrab.grab()
    w, h = screen.size
    top = screen.crop((0, 0, w, h // 5))
    arr = np.array(top)

    r, g, b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
    cr, cg, cb = BANNER_COLOR_RGB
    t = COLOR_TOLERANCE

    mask = (
        (r > cr - t) & (r < cr + t) &
        (g > cg - t) & (g < cg + t) &
        (b > cb - t) & (b < cb + t)
    )
    count = int(np.sum(mask))
    print(f"[debug] Banner pixel count: {count}")
    return count > 300

# ── Main ──────────────────────────────────────────────────

def watch_auto():
    tg("👀 Watchdog chạy - tự động detect banner limit...")
    print("Đang theo dõi tự động... Ctrl+C để dừng")
    alerted = False
    while True:
        if has_limit_banner() and not alerted:
            alerted = True
            threading.Thread(target=wait_retry, daemon=True).start()
        elif not has_limit_banner():
            alerted = False
        time.sleep(10)

def watch_hotkey():
    tg("👀 Watchdog chạy - bấm Ctrl+F9 khi thấy limit...")
    print("Bấm Ctrl+F9 khi thấy limit. Ctrl+C để dừng")
    keyboard.add_hotkey(
        "ctrl+f9",
        lambda: threading.Thread(target=wait_retry, daemon=True).start()
    )
    keyboard.wait()

if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "auto"
    if mode == "auto":
        watch_auto()
    elif mode == "hotkey":
        watch_hotkey()