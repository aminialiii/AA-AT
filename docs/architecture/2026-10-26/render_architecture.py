"""Render the documented AA-AT architecture; research documentation only.

No imports from the trading service, no network access, and no writes outside
the directory containing this file. SVG remains editable in a vector editor;
the paired Mermaid sources are editable structural views.
"""
from __future__ import annotations

from html import escape
from pathlib import Path


HERE = Path(__file__).resolve().parent
INK = "#17324d"
MUTED = "#587087"
COLORS = {
    "blue": ("#eaf3ff", "#70a6e8", "#2874c7"),
    "green": ("#ecf8f0", "#8dcea2", "#258455"),
    "red": ("#fff0ef", "#ed9b99", "#bb4e4c"),
    "purple": ("#f4efff", "#b9a5e7", "#7958b7"),
    "cyan": ("#eafaff", "#82ccdb", "#248ca2"),
    "amber": ("#fff7e8", "#e6c081", "#ac7425"),
    "gray": ("#f0f3f6", "#bac5cf", "#718091"),
}


class Sheet:
    def __init__(self, width: int, height: int, title: str, subtitle: str):
        self.w, self.h = width, height
        self.parts: list[str] = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">',
            '<defs><filter id="shadow" x="-20%" y="-30%" width="140%" height="170%">'
            '<feDropShadow dx="0" dy="5" stdDeviation="7" flood-color="#93a8bc" flood-opacity=".16"/>'
            '</filter><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="5" '
            'orient="auto" markerUnits="userSpaceOnUse"><path d="M1 1 L9 5 L1 9" fill="none" '
            'stroke="#64839f" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></marker>'
            '<marker id="darrow" markerWidth="10" markerHeight="10" refX="8" refY="5" '
            'orient="auto" markerUnits="userSpaceOnUse"><path d="M1 1 L9 5 L1 9" fill="none" '
            'stroke="#9c83c3" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></marker></defs>',
            f'<rect width="{width}" height="{height}" fill="#f8fafc"/>',
            f'<text x="{width-64}" y="73" text-anchor="end" font-size="38" font-weight="700" '
            f'fill="{INK}" font-family="Tahoma, Segoe UI, sans-serif">{escape(title)}</text>',
            f'<text x="{width-64}" y="107" text-anchor="end" font-size="19" '
            f'fill="{MUTED}" font-family="Tahoma, Segoe UI, sans-serif">{escape(subtitle)}</text>',
            '<line x1="60" y1="125" x2="1740" y2="125" stroke="#dce6ee" stroke-width="2"/>'
            if width == 1800 else
            f'<line x1="60" y1="125" x2="{width-60}" y2="125" stroke="#dce6ee" stroke-width="2"/>',
        ]

    def rect(self, x: int, y: int, w: int, h: int, color: str,
             *, radius: int = 23, shadow: bool = False) -> None:
        bg, stroke, _ = COLORS[color]
        effect = ' filter="url(#shadow)"' if shadow else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" '
            f'fill="{bg}" stroke="{stroke}" stroke-width="2"{effect}/>'
        )

    def txt(self, x: int, y: int, value: str, *, size: int = 21,
            bold: bool = False, color: str = INK, rtl: bool = True,
            anchor: str | None = None) -> None:
        # SVG text-anchor follows the inline direction. For RTL, "start" is
        # the right edge; "end" would push Persian text beyond the card.
        align = anchor or "start"
        direction = ' direction="rtl" unicode-bidi="plaintext"' if rtl else ""
        weight = "700" if bold else "400"
        self.parts.append(
            f'<text x="{x}" y="{y}" text-anchor="{align}"{direction} '
            f'font-size="{size}" font-weight="{weight}" fill="{color}" '
            f'font-family="Tahoma, Segoe UI, sans-serif">{escape(value)}</text>'
        )

    def group(self, x: int, y: int, w: int, h: int, color: str,
              fa: str, en: str, note: str = "") -> None:
        self.rect(x, y, w, h, color)
        _, _, accent = COLORS[color]
        self.parts.append(f'<circle cx="{x+29}" cy="{y+34}" r="11" fill="{accent}"/>')
        self.txt(x+w-25, y+42, fa, size=26, bold=True)
        self.txt(x+50, y+42, en, size=16, color=accent, rtl=False)
        if note:
            self.txt(x+w-25, y+72, note, size=17, color=MUTED)

    def card(self, x: int, y: int, w: int, h: int, color: str,
             fa: str, en: str, note: str = "", *, muted: bool = False) -> None:
        _, stroke, accent = COLORS[color]
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" '
            f'fill="#ffffff" stroke="{stroke}" stroke-width="1.7" filter="url(#shadow)"/>'
        )
        self.parts.append(f'<rect x="{x}" y="{y}" width="7" height="{h}" rx="3" fill="{accent}"/>')
        self.txt(x+w-18, y+34, fa, size=21 if not muted else 19, bold=True)
        self.txt(x+18, y+58, en, size=15, color=accent, rtl=False)
        if note:
            self.txt(x+w-18, y+h-14, note, size=15, color=MUTED)

    def arrow(self, path: str, *, dashed: bool = False,
              label: str | None = None, label_x: int = 0, label_y: int = 0) -> None:
        stroke = "#9c83c3" if dashed else "#64839f"
        dash = ' stroke-dasharray="8 6"' if dashed else ""
        marker = "darrow" if dashed else "arrow"
        self.parts.append(
            f'<path d="{path}" fill="none" stroke="{stroke}" stroke-width="2.5"'
            f'{dash} marker-end="url(#{marker})"/>'
        )
        if label:
            self.txt(label_x, label_y, label, size=15, color=MUTED)

    def legend(self, y: int, *, width: int | None = None) -> None:
        width = width or self.w
        self.parts.append(f'<rect x="60" y="{y}" width="{width-120}" height="85" rx="20" fill="#ffffff" stroke="#dce6ee"/>')
        self.txt(width-85, y+30, "راهنمای وضعیت و اتصال", size=20, bold=True)
        self.parts.append(f'<path d="M{width-330} {y+55} H{width-270}" stroke="#64839f" stroke-width="3" marker-end="url(#arrow)"/>')
        self.txt(width-345, y+60, "پیوند پیاده‌سازی‌شده", size=16)
        self.parts.append(f'<path d="M{width-730} {y+55} H{width-670}" stroke="#9c83c3" stroke-width="3" stroke-dasharray="8 6" marker-end="url(#darrow)"/>')
        self.txt(width-745, y+60, "پژوهشی یا تأییدنشده", size=16)
        self.txt(410, y+57, "خاکستری = مسدود یا نامعلوم", size=16)

    def save(self, path: Path) -> None:
        self.parts.append("</svg>")
        path.write_text("\n".join(self.parts) + "\n", encoding="utf-8")


def hld() -> None:
    s = Sheet(1800, 1080, "AA-AT — High-Level Architecture (HLD)",
              "نمای اجرایی · پیاده‌سازی با وضعیت عملیاتی جداگانه · ۲۶ اکتبر ۲۰۲۶")
    s.group(60, 150, 1680, 278, "blue", "معاملات دمو ـ حفاظت‌شده", "PROTECTED DEMO TRADING",
            "پنج مسیر S01–S05 پیاده‌سازی‌شده؛ فعال‌بودن فقط با heartbeat تازه قابل تأیید است")
    xs = [85, 365, 645, 925, 1205, 1485]
    rows = [
        ("ترمینال MT5 دمو", "MT5 DEMO", "هویت حساب و قیمت"),
        ("داده و سیگنال", "M1 / SIGNALS", "کندل تکمیل‌شده"),
        ("کارگران S01–S05", "PYTHON WORKERS", "قواعد منجمد"),
        ("ناظر ریسک", "RISK SUPERVISOR", "سیاست مؤثر v4"),
        ("ارسال سفارش", "BROKER ROUTING", "گیت‌های دمو"),
        ("تطبیق و دفترکل", "RECONCILIATION", "شواهد بروکر"),
    ]
    for x, item in zip(xs, rows):
        s.card(x, 258, 230, 103, "blue" if x not in (925, 1205) else "red", *item)
    for a, b in zip(xs, xs[1:]):
        s.arrow(f"M{a+230} 310 H{b-7}")
    s.rect(670, 376, 460, 38, "gray", radius=12)
    s.txt(1110, 403, "S06–S18: مسیر اجرایی تأییدنشده", size=19, bold=True)
    s.arrow("M1600 361 V441 H1050 V548", label="فقط‌خواندنی", label_x=1320, label_y=438)

    s.group(60, 455, 815, 232, "cyan", "پایش و کنترل", "MONITORING & CONTROL")
    for x, item in zip([85, 345, 605], [
        ("مرکز فرمان", "PORT 8765", "تله‌متری خواندنی"),
        ("گراف دانش", "GRAPHIFY", "نقشهٔ ایستا"),
        ("API کنترل", "CONTROL API", "پل عملیاتی تأییدنشده"),
    ]):
        s.card(x, 542, 235, 108, "cyan" if x != 605 else "gray", *item)

    s.group(905, 455, 835, 442, "purple", "پژوهش مستقل", "ISOLATED RESEARCH",
            "مسیر تحلیل فقط‌خواندنی؛ خروجی شبیه‌سازی از سود/زیان دمو جداست")
    for x, y, item in [
        (930, 555, ("گردآورنده", "READ-ONLY COLLECTOR", "ورودی شواهد")),
        (1190, 555, ("انبار پژوهش", "RESEARCH WAREHOUSE", "داده و منشأ")),
        (1450, 555, ("داشبورد پژوهش", "PORT 8775", "وضعیت پژوهش")),
        (930, 705, ("دادهٔ تاریخی", "MARKET HISTORY", "پوشش ناقص")),
        (1190, 705, ("MT5 جدا + EA S04", "ISOLATED TESTER", "تستر هنوز مسدود")),
        (1450, 705, ("بازار و تقویم", "STATUS / NEWS", "منبع زنده تأییدنشده")),
    ]:
        s.card(x, y, 235, 112, "purple" if x != 1450 or y != 705 else "gray", *item)
    s.arrow("M1165 611 H1183", label="فقط‌خواندنی", label_x=1175, label_y=538)
    s.arrow("M1425 611 H1443")
    s.arrow("M1165 761 H1183", dashed=True)
    s.arrow("M1425 761 H1443", dashed=True)
    s.txt(1675, 868, "XAUUSD: پژوهش تاریخی جدا؛ مجوز DEMO در سیاست v4 مستقل است", size=17, color=MUTED)

    s.group(60, 715, 815, 184, "amber", "خدمات پشتیبان", "SUPPORTING SERVICES")
    for x, item in zip([85, 345, 605], [
        ("پشتیبان سه‌اسلات", "V1 / V2 / V3", "دورهٔ ۲۴ ساعته"),
        ("همگام‌سازی Git", "EVERY 4 HOURS", "شاخهٔ بازبینی"),
        ("شاخه‌های پژوهش", "REVIEW WORKFLOW", "بدون merge خودکار"),
    ]):
        s.card(x, 792, 235, 90, "amber", *item)
    s.legend(938)
    s.save(HERE / "AA-AT-HLD.svg")


def lld() -> None:
    s = Sheet(2400, 1570, "AA-AT — Low-Level Architecture (LLD)",
              "جریان داده، مرز فرایندها و گیت‌های ایمنی · مقادیر سیاست مؤثر v4، نه متن تاریخی ۲٪")
    s.group(55, 145, 2290, 445, "blue", "جریان اجرای DEMO؛ یک سرویس Python با پنج حلقهٔ کارگر", "TRADING EXECUTION SERVICE",
            "MT5 و پایگاه عملیاتی بیرون از مسیر پژوهش هستند؛ وضعیت زنده از heartbeat و تطبیق بروکر سنجیده می‌شود")
    flow = [
        ("اتصال MT5", "BROKER.GUARD", "DEMO + hedging"),
        ("دریافت M1", "COPY_RATES", "قیمت تازه"),
        ("قواعد منجمد", "ENGINE / SIGNALS", "S01–S05"),
        ("حلقهٔ کارگران", "WORKER_LOOP", "S06–S18 blocked"),
        ("کنترل ریسک", "EQUITY_GATE", "حد ضرر + هزینه"),
        ("قفل پذیرش", "ROUTE LOCK", "slots + intent"),
        ("گیت ارسال", "BROKER.SEND", "بررسی دوباره"),
        ("تطبیق بروکر", "RECONCILE", "ledger + evidence"),
    ]
    xx = [82 + i*283 for i in range(8)]
    for i, (x, item) in enumerate(zip(xx, flow)):
        color = "red" if i in (4, 5, 6) else "green" if i in (1, 2) else "blue"
        s.card(x, 255, 253, 116, color, *item)
    for a, b in zip(xx, xx[1:]):
        s.arrow(f"M{a+253} 313 H{b-7}")
    s.rect(82, 400, 2232, 144, "red", radius=17)
    s.txt(2288, 430, "سیاست مؤثر ریسک و توقف ـ v4", size=22, bold=True)
    s.txt(2288, 465, "۵ موقعیت/سفارش معلق · ریسک باز و معلق ≤۱۰٪ اکوئیتی · توقف زیان روزانه ۵٪ · افت قلهٔ اکوئیتی ۱۰٪", size=20)
    s.txt(2288, 499, "غیرطلا: ۰٫۲۵٪ سهم مجازی کارگر · طلا: کمینهٔ ۱۰ دلار، ۱٪ اکوئیتی و فضای باقیماندهٔ توقف‌ها", size=19)
    s.txt(2288, 529, "فایل توقف اضطراری، breaker، انقضای سیگنال و مالکیت موقعیت باید قبل از ارسال معتبر باشند", size=17, color=MUTED)

    s.group(55, 620, 1120, 293, "cyan", "پایش و رابط‌ها", "MONITORING & INTERFACES",
            "داشبورد سفارش ارسال نمی‌کند؛ پل فرمانِ سرویس باید جداگانه عملیاتی تأیید شود")
    for x, item in zip([82, 372, 662, 952], [
        ("status.json", "HEARTBEAT", "زمان‌دار"),
        ("مرکز فرمان", "HTTP :8765", "احراز هویت"),
        ("API پژوهش", "READ-ONLY", "مستندات"),
        ("پل کنترل", "UNVERIFIED", "غیرفعال"),
    ]):
        s.card(x, 735, 250 if x != 952 else 195, 110,
               "gray" if x == 952 else "cyan", *item)
    s.arrow("M332 790 H365")
    s.arrow("M622 790 H655")
    s.arrow("M912 790 H945", dashed=True)

    s.group(1205, 620, 1140, 293, "amber", "ذخیره و سرویس‌های پشتیبان", "STORAGE & SUPPORT",
            "پشتیبان و Git مستقل از محاسبات سیگنال؛ هیچ انتشار خودکار به سرویس معامله")
    for x, item in zip([1232, 1512, 1792, 2072], [
        ("دفترکل", "SQLITE + EVIDENCE", "شناسه‌های بروکر"),
        ("پشتیبان", "V1 / V2 / V3", "هر ۲۴ ساعت"),
        ("Git sync", "4H REVIEW BRANCH", "بدون deploy"),
        ("نقاط ادامه", "CHECKPOINTS", "وضعیت ثبت‌شده"),
    ]):
        s.card(x, 735, 247 if x != 2072 else 245, 110, "amber", *item)
    s.arrow("M1355 845 V929 H873 V1058", label="نسخهٔ فقط‌خواندنی", label_x=1150, label_y=927)

    s.group(55, 950, 2290, 407, "purple", "پژوهش جدا از اجرا", "ISOLATED RESEARCH PIPELINE",
            "خواندن دادهٔ عملیاتی فقط از نسخهٔ جدا/مسیر پژوهش؛ تستر و شبیه‌سازی فاقد دسترسی مسیر سفارش DEMO")
    research = [
        ("دریافت تاریخی", "BROKER / EXTERNAL", "XAUUSD نیز"),
        ("کیفیت و منشأ", "COVERAGE GATE", "UTC + checksum"),
        ("انبار پژوهش", "CATALOG / VAULT", "دادهٔ جدا"),
        ("برابری S04", "PY ↔ MQL5", "runtime تأییدنشده"),
        ("تستر MT5", "ISOLATED TESTER", "بدون حساب"),
        ("نتایج تاریخی", "BACKTEST INDEX", "صفر اجرا"),
        ("داشبورد", "HTTP :8775", "فقط پژوهش"),
    ]
    rx = [82 + i*323 for i in range(7)]
    for i, (x, item) in enumerate(zip(rx, research)):
        s.card(x, 1065, 290, 120, "gray" if i in (3, 4, 5) else "purple", *item)
    for a, b in zip(rx, rx[1:]):
        s.arrow(f"M{a+290} 1125 H{b-8}", dashed=True)
    s.card(82, 1225, 510, 95, "green", "وضعیت بازار و نشست‌ها", "MARKET STATUS ENGINE", "بدون برنامهٔ بروکرِ تأییدشده")
    s.card(618, 1225, 510, 95, "gray", "تقویم اقتصادی و خبر", "ECONOMIC CALENDAR", "رویداد معتبر وارد نشده")
    s.card(1154, 1225, 510, 95, "gray", "پوشش داده و نرخ‌دهی", "PARTIAL / HTTP 429", "دادهٔ سه‌ساله ناکافی")
    s.card(1690, 1225, 628, 95, "gray", "مانع‌های عملیاتی پژوهش", "NO ACCOUNT / NO MQL RUNTIME PARITY", "بدون نتیجهٔ backtest معتبر")
    s.legend(1412, width=2400)
    s.save(HERE / "AA-AT-LLD.svg")


if __name__ == "__main__":
    hld()
    lld()
