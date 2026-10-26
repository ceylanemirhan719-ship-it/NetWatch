
import customtkinter as ctk
import tkinter as tk
import subprocess
import re
import threading
import speedtest
import csv
import os
from datetime import datetime

# --------------------------------------------------
# AYARLAR
# --------------------------------------------------

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BG = "#0B1120"
SIDEBAR = "#0F172A"
PANEL = "#151F32"
PANEL_LIGHT = "#1B2940"
BORDER = "#263650"
BLUE = "#3B82F6"
CYAN = "#22D3EE"
GREEN = "#34D399"
YELLOW = "#FBBF24"
RED = "#F87171"
TEXT = "#F1F5F9"
MUTED = "#94A3B8"

LOG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "netwatch_log.csv"
)

window = ctk.CTk()
window.title("NetWatch | Network Monitor")
window.geometry("1200x760")
window.minsize(1000, 680)
window.configure(fg_color=BG)

current_page = "dashboard"
testing = False

# --------------------------------------------------
# CSV OKUMA
# --------------------------------------------------

def read_logs():
    if not os.path.exists(LOG_FILE):
        return []

    rows = []

    try:
        with open(
            LOG_FILE, "r", newline="", encoding="utf-8-sig"
        ) as file:
            sample = file.read(2048)
            file.seek(0)

            delimiter = ";" if sample.count(";") >= sample.count(",") else ","
            reader = csv.DictReader(file, delimiter=delimiter)

            for row in reader:
                normalized = {
                    (key or "").strip().lower(): (value or "").strip()
                    for key, value in row.items()
                }

                date = normalized.get("tarih", "")
                time = normalized.get("saat", "")
                ping = normalized.get("ping", "")

                download = (
                    normalized.get("download (mbps)")
                    or normalized.get("download")
                    or ""
                )
                upload = (
                    normalized.get("upload (mbps)")
                    or normalized.get("upload")
                    or ""
                )
                quality = normalized.get("kalite", "")
                description = normalized.get("açıklama", "")

                # Önceki sürümde İngilizce başlık kullanılmış olabilir.
                date = date or normalized.get("date", "")
                time = time or normalized.get("time", "")
                ping = ping or normalized.get("ping (ms)", "")
                quality = quality or normalized.get("quality", "")
                description = description or normalized.get("description", "")

                if date or time or ping or download or upload:
                    rows.append({
                        "date": date,
                        "time": time,
                        "ping": ping,
                        "download": download,
                        "upload": upload,
                        "quality": quality,
                        "description": description,
                    })

    except (OSError, csv.Error) as error:
        print("Log okuma hatası:", error)

    return rows


def numeric(value):
    try:
        cleaned = (
            str(value)
            .lower()
            .replace("mbps", "")
            .replace("ms", "")
            .replace(",", ".")
            .replace("<", "")
            .strip()
        )
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def save_log(ping, download, upload, score, description):
    file_exists = os.path.exists(LOG_FILE)
    needs_header = (
        not file_exists
        or os.path.getsize(LOG_FILE) == 0
    )

    try:
        with open(
            LOG_FILE,
            "a",
            newline="",
            encoding="utf-8-sig"
        ) as file:
            writer = csv.writer(file, delimiter=";")

            if needs_header:
                writer.writerow([
                    "Tarih",
                    "Saat",
                    "Ping",
                    "Download (Mbps)",
                    "Upload (Mbps)",
                    "Kalite",
                    "Açıklama"
                ])

            now = datetime.now()

            writer.writerow([
                now.strftime("%d.%m.%Y"),
                now.strftime("%H:%M:%S"),
                ping,
                round(download, 2),
                round(upload, 2),
                f"{score}/5" if score is not None else "Ölçülemedi",
                description
            ])

    except OSError as error:
        print("Log kaydedilemedi:", error)
        window.after(
            0,
            lambda: status_label.configure(
                text="Sonuç ölçüldü ancak log kaydedilemedi."
            )
        )


# --------------------------------------------------
# ÖLÇÜM VE PUANLAMA
# --------------------------------------------------

def measure_ping():
    try:
        result = subprocess.run(
            ["ping", "-n", "1", "-w", "3000", "1.1.1.1"],
            capture_output=True,
            text=True,
            timeout=5
        )

        match = re.search(
            r"time[=<](\d+)ms",
            result.stdout,
            re.IGNORECASE
        )

        if match:
            return f"{match.group(1)} ms"

        if re.search(r"time<1ms", result.stdout, re.IGNORECASE):
            return "<1 ms"

        return "Başarısız"

    except (subprocess.TimeoutExpired, OSError):
        return "Başarısız"


def calculate_quality(ping_text, download, upload):
    if ping_text == "Başarısız":
        return None, "Ping ölçülemedi"

    try:
        ping = float(
            ping_text.replace("ms", "")
            .replace("<", "")
            .strip()
        )
    except ValueError:
        return None, "Ping ölçülemedi"

    ping_score = max(0, 50 * (1 - ping / 200))
    download_score = min(30, download / 100 * 30)
    upload_score = min(20, upload)

    total = ping_score + download_score + upload_score
    score = max(1, min(5, round(total / 20)))

    descriptions = {
        1: "Çok zayıf",
        2: "Zayıf",
        3: "Orta",
        4: "İyi",
        5: "Çok iyi"
    }

    return score, descriptions[score]


# --------------------------------------------------
# ARAYÜZ YARDIMCILARI
# --------------------------------------------------

def make_label(parent, text, size=13, color=TEXT, bold=False):
    return ctk.CTkLabel(
        parent,
        text=text,
        font=("Segoe UI", size, "bold" if bold else "normal"),
        text_color=color
    )


def make_card(parent, title, icon, accent):
    card = ctk.CTkFrame(
        parent,
        fg_color=PANEL,
        corner_radius=16,
        border_width=1,
        border_color=BORDER
    )

    make_label(
        card, f"{icon}   {title}", 13, MUTED, True
    ).pack(anchor="w", padx=18, pady=(17, 8))

    value = make_label(card, "--", 27, TEXT, True)
    value.pack(anchor="w", padx=18)

    detail = make_label(card, "Henüz ölçülmedi", 11, accent)
    detail.pack(anchor="w", padx=18, pady=(5, 16))

    return card, value, detail


# --------------------------------------------------
# ANA YERLEŞİM
# --------------------------------------------------

root_frame = ctk.CTkFrame(window, fg_color=BG, corner_radius=0)
root_frame.pack(fill="both", expand=True)

sidebar = ctk.CTkFrame(
    root_frame,
    width=220,
    fg_color=SIDEBAR,
    corner_radius=0
)
sidebar.pack(side="left", fill="y")
sidebar.pack_propagate(False)

content = ctk.CTkFrame(root_frame, fg_color=BG, corner_radius=0)
content.pack(side="left", fill="both", expand=True)

# Kenar menüsü
make_label(sidebar, "◈  NetWatch", 25, CYAN, True).pack(
    anchor="w", padx=22, pady=(28, 4)
)
make_label(sidebar, "NETWORK MONITOR", 10, MUTED, True).pack(
    anchor="w", padx=24, pady=(0, 35)
)

nav_buttons = {}

def set_nav_style(active):
    for name, button in nav_buttons.items():
        button.configure(
            fg_color=PANEL_LIGHT if name == active else "transparent",
            text_color=TEXT if name == active else MUTED
        )


def show_page(page):
    global current_page
    current_page = page

    set_nav_style(page)

    dashboard_page.pack_forget()
    history_page.pack_forget()

    if page == "dashboard":
        dashboard_page.pack(fill="both", expand=True)
        refresh_dashboard()
    else:
        history_page.pack(fill="both", expand=True)
        refresh_history()


def add_nav(label, page):
    button = ctk.CTkButton(
        sidebar,
        text=label,
        height=44,
        corner_radius=10,
        anchor="w",
        font=("Segoe UI", 13, "bold"),
        fg_color="transparent",
        hover_color=PANEL_LIGHT,
        text_color=MUTED,
        command=lambda: show_page(page)
    )
    button.pack(fill="x", padx=14, pady=4)
    nav_buttons[page] = button


add_nav("⌂   Genel Bakış", "dashboard")
add_nav("▤   Test Geçmişi", "history")

sidebar_bottom = ctk.CTkFrame(sidebar, fg_color="transparent")
sidebar_bottom.pack(side="bottom", fill="x", padx=18, pady=22)

make_label(sidebar_bottom, "NETWATCH 1.0", 11, MUTED, True).pack(
    anchor="w"
)
make_label(sidebar_bottom, "Yerel ölçüm paneli", 10, MUTED).pack(
    anchor="w", pady=(4, 0)
)

# Sayfalar
dashboard_page = ctk.CTkFrame(content, fg_color=BG, corner_radius=0)
history_page = ctk.CTkFrame(content, fg_color=BG, corner_radius=0)


# --------------------------------------------------
# GENEL BAKIŞ SAYFASI
# --------------------------------------------------

header = ctk.CTkFrame(dashboard_page, fg_color="transparent")
header.pack(fill="x", padx=28, pady=(24, 15))

header_left = ctk.CTkFrame(header, fg_color="transparent")
header_left.pack(side="left")

make_label(header_left, "Genel Bakış", 26, TEXT, True).pack(anchor="w")
make_label(
    header_left,
    "İnternet bağlantının performansını takip et.",
    12,
    MUTED
).pack(anchor="w", pady=(4, 0))

start_button = ctk.CTkButton(
    header,
    text="▶   Testi Başlat",
    width=165,
    height=42,
    corner_radius=11,
    fg_color=BLUE,
    hover_color="#2563EB",
    font=("Segoe UI", 13, "bold")
)
start_button.pack(side="right", padx=(10, 0))

cards = ctk.CTkFrame(dashboard_page, fg_color="transparent")
cards.pack(fill="x", padx=22, pady=8)

ping_card, ping_value, ping_detail = make_card(
    cards, "PING", "◉", CYAN
)
download_card, download_value, download_detail = make_card(
    cards, "DOWNLOAD", "↓", GREEN
)
upload_card, upload_value, upload_detail = make_card(
    cards, "UPLOAD", "↑", "#A78BFA"
)
quality_card, quality_value, quality_detail = make_card(
    cards, "KALİTE", "★", YELLOW
)

for column, card in enumerate([
    ping_card, download_card, upload_card, quality_card
]):
    cards.grid_columnconfigure(column, weight=1, uniform="metric")
    card.grid(
        row=0, column=column, sticky="nsew",
        padx=6, pady=6
    )

status_panel = ctk.CTkFrame(
    dashboard_page,
    fg_color=PANEL,
    corner_radius=12
)
status_panel.pack(fill="x", padx=28, pady=(8, 14))

status_label = make_label(
    status_panel, "●  Hazır — Test başlatılabilir", 12, GREEN
)
status_label.pack(anchor="w", padx=16, pady=12)

# Grafik alanı
graph_panel = ctk.CTkFrame(
    dashboard_page,
    fg_color=PANEL,
    corner_radius=16,
    border_width=1,
    border_color=BORDER
)
graph_panel.pack(
    fill="both", expand=True, padx=28, pady=(0, 22)
)

graph_header = ctk.CTkFrame(graph_panel, fg_color="transparent")
graph_header.pack(fill="x", padx=18, pady=(15, 5))

make_label(
    graph_header, "Performans Geçmişi", 16, TEXT, True
).pack(side="left")

make_label(
    graph_header, "Son 12 ölçüm", 11, MUTED
).pack(side="right")

chart = tk.Canvas(
    graph_panel,
    bg=PANEL,
    highlightthickness=0,
    height=230
)
chart.pack(fill="both", expand=True, padx=12, pady=(0, 12))


def draw_graph():
    chart.delete("all")

    width = max(chart.winfo_width(), 500)
    height = max(chart.winfo_height(), 180)

    rows = read_logs()[-12:]

    left, right = 48, width - 22
    top, bottom = 22, height - 35

    # Grafik ızgarası
    for i in range(5):
        y = top + (bottom - top) * i / 4
        chart.create_line(
            left, y, right, y,
            fill=BORDER, dash=(2, 4)
        )

    if len(rows) < 2:
        chart.create_text(
            width / 2,
            height / 2,
            text="Grafik için en az iki ölçüm kaydet.",
            fill=MUTED,
            font=("Segoe UI", 12)
        )
        return

    downloads = [numeric(row["download"]) for row in rows]
    pings = [numeric(row["ping"]) for row in rows]

    def draw_series(values, color, label, x_offset=0):
        valid = [value for value in values if value is not None]
        if len(valid) < 2:
            return

        maximum = max(max(valid), 1) * 1.15
        points = []

        for index, value in enumerate(values):
            if value is None:
                continue

            x = left + (right - left) * index / (len(values) - 1)
            y = bottom - (bottom - top) * value / maximum
            points.extend([x + x_offset, y])

        if len(points) >= 4:
            chart.create_line(
                *points, fill=color, width=3, smooth=True
            )

            for index in range(0, len(points), 2):
                chart.create_oval(
                    points[index] - 3,
                    points[index + 1] - 3,
                    points[index] + 3,
                    points[index + 1] + 3,
                    fill=color,
                    outline=color
                )

    draw_series(downloads, GREEN, "Download")
    draw_series(pings, CYAN, "Ping")

    chart.create_text(
        left, height - 13,
        text=rows[0]["time"],
        fill=MUTED,
        anchor="w",
        font=("Segoe UI", 9)
    )
    chart.create_text(
        right, height - 13,
        text=rows[-1]["time"],
        fill=MUTED,
        anchor="e",
        font=("Segoe UI", 9)
    )


# --------------------------------------------------
# TEST GEÇMİŞİ SAYFASI
# --------------------------------------------------

history_header = ctk.CTkFrame(history_page, fg_color="transparent")
history_header.pack(fill="x", padx=28, pady=(25, 18))

history_header_left = ctk.CTkFrame(
    history_header, fg_color="transparent"
)
history_header_left.pack(side="left")

make_label(history_header_left, "Test Geçmişi", 26, TEXT, True).pack(
    anchor="w"
)
make_label(
    history_header_left,
    "CSV dosyasına kaydedilen ölçümler.",
    12, MUTED
).pack(anchor="w", pady=(4, 0))

refresh_button = ctk.CTkButton(
    history_header,
    text="↻  Yenile",
    width=110,
    height=38,
    fg_color=PANEL_LIGHT,
    hover_color=BORDER,
    command=lambda: refresh_history()
)
refresh_button.pack(side="right")

history_summary = ctk.CTkFrame(
    history_page, fg_color=PANEL, corner_radius=12
)
history_summary.pack(fill="x", padx=28, pady=(0, 14))

history_count_label = make_label(
    history_summary, "Toplam kayıt: 0", 13, TEXT, True
)
history_count_label.pack(anchor="w", padx=16, pady=13)

table_panel = ctk.CTkFrame(
    history_page,
    fg_color=PANEL,
    corner_radius=14,
    border_width=1,
    border_color=BORDER
)
table_panel.pack(
    fill="both", expand=True, padx=28, pady=(0, 25)
)

table_header = ctk.CTkFrame(table_panel, fg_color=PANEL_LIGHT)
table_header.pack(fill="x", padx=10, pady=(10, 5))

columns = [
    ("Tarih", 0.19),
    ("Saat", 0.15),
    ("Ping", 0.13),
    ("Download", 0.17),
    ("Upload", 0.15),
    ("Kalite", 0.21)
]

for column_index, (name, weight) in enumerate(columns):
    table_header.grid_columnconfigure(column_index, weight=1)
    make_label(
        table_header, name, 11, MUTED, True
    ).grid(
        row=0, column=column_index, padx=5, pady=12, sticky="w"
    )

history_rows_frame = ctk.CTkScrollableFrame(
    table_panel,
    fg_color="transparent",
    corner_radius=0
)
history_rows_frame.pack(
    fill="both", expand=True, padx=10, pady=(0, 10)
)


def refresh_history():
    for child in history_rows_frame.winfo_children():
        child.destroy()

    rows = read_logs()
    history_count_label.configure(
        text=f"Toplam kayıt: {len(rows)}"
    )

    if not rows:
        make_label(
            history_rows_frame,
            "Henüz kayıt yok. Genel Bakış bölümünden test başlat.",
            13, MUTED
        ).pack(pady=30)
        return

    for row_index, item in enumerate(reversed(rows)):
        row_frame = ctk.CTkFrame(
            history_rows_frame,
            fg_color=PANEL_LIGHT if row_index % 2 == 0 else PANEL,
            corner_radius=8
        )
        row_frame.pack(fill="x", pady=3)

        values = [
            item["date"] or "-",
            item["time"] or "-",
            item["ping"] or "-",
            f'{item["download"]} Mbps' if item["download"] else "-",
            f'{item["upload"]} Mbps' if item["upload"] else "-",
            item["quality"] or "-"
        ]

        for column_index, (value, (_, weight)) in enumerate(
            zip(values, columns)
        ):
            row_frame.grid_columnconfigure(column_index, weight=1)

            color = TEXT
            if column_index == 5:
                if value.startswith("4") or value.startswith("5"):
                    color = GREEN
                elif value.startswith("3"):
                    color = YELLOW
                elif value.startswith("1") or value.startswith("2"):
                    color = RED

            make_label(
                row_frame, value, 11, color
            ).grid(
                row=0,
                column=column_index,
                padx=5,
                pady=11,
                sticky="w"
            )


# --------------------------------------------------
# SONUÇLARI GÜNCELLEME
# --------------------------------------------------

def show_results(ping, download, upload):
    global testing
    testing = False

    ping_value.configure(text=ping)
    download_value.configure(text=f"{download:.2f} Mbps")
    upload_value.configure(text=f"{upload:.2f} Mbps")

    ping_number = numeric(ping)
    ping_detail.configure(
        text=(
            "Gecikme ölçümü"
            if ping_number is not None
            else "Ping ölçülemedi"
        )
    )

    download_detail.configure(text="İndirme hızı")
    upload_detail.configure(text="Yükleme hızı")

    score, description = calculate_quality(
        ping, download, upload
    )

    quality_value.configure(
        text=f"{score}/5" if score is not None else "-- / 5"
    )
    quality_detail.configure(text=description)

    status_label.configure(
        text="●  Test tamamlandı",
        text_color=GREEN
    )
    start_button.configure(
        state="normal",
        text="▶   Testi Başlat"
    )

    save_log(ping, download, upload, score, description)
    refresh_dashboard()


def show_error(message):
    global testing
    testing = False

    status_label.configure(
        text="●  Hız testi başarısız. Ayrıntı terminalde.",
        text_color=RED
    )
    start_button.configure(
        state="normal",
        text="▶   Tekrar Dene"
    )
    print("Hız testi hatası:", message)


def refresh_dashboard():
    draw_graph()


def run_tests():
    try:
        window.after(
            0,
            lambda: status_label.configure(
                text="●  Ping ölçülüyor...",
                text_color=CYAN
            )
        )

        ping = measure_ping()

        window.after(
            0,
            lambda: status_label.configure(
                text="●  İndirme ve yükleme ölçülüyor...",
                text_color=CYAN
            )
        )

        st = speedtest.Speedtest()
        st.get_best_server()

        download = st.download() / 1_000_000
        upload = st.upload() / 1_000_000

        window.after(
            0,
            lambda p=ping, d=download, u=upload:
                show_results(p, d, u)
        )

    except Exception as error:
        message = str(error)
        window.after(
            0,
            lambda msg=message: show_error(msg)
        )


def start_test():
    global testing

    if testing:
        return

    testing = True
    start_button.configure(
        state="disabled",
        text="Test yapılıyor..."
    )
    status_label.configure(
        text="●  Bağlantı testi başlatıldı...",
        text_color=CYAN
    )

    threading.Thread(
        target=run_tests,
        daemon=True
    ).start()


start_button.configure(command=start_test)

# Pencere boyutu değişince grafiği yenile
chart.bind("<Configure>", lambda event: draw_graph())

# İlk açılış
set_nav_style("dashboard")
dashboard_page.pack(fill="both", expand=True)

refresh_dashboard()
refresh_history()

window.mainloop()
