# TENNIS-SIGNAL-DASHBORD

**موتور پایه نجومی-جمتریا تورنمنت / شهر / کورت مسابقه تنیس (بدون تاریخ تولد)**  
*(Cloned cleanly from `NBA-SIGNAL-DASHBORD.zip` — 100% isolated from all `NBA-*` and `NHL-*` repositories, sheets, and state files)*

---

## قوانین قطعی معماری نجومی-جمتریا (Astro-Gematria Architecture)

1. **مطلقاً بدون تاریخ تولد بازیکنان (`BIRTHDATE_USED = False`):**  
   تمامی محاسبات بازیکن و تورنمنت منحصراً بر پایه **جمتریا انگلیسی نام‌ها (`EGEM_MAP`: نام بازیکن / نام تورنمنت، شهر و کورت)** + **موقعیت سیارات در لحظه و مختصات مسابقه (`pyswisseph`)** + **درجه پایه ثابت تور (`DEG1`)** انجام می‌شود.

2. **پروفایل‌های ثابت نجومی-جمتریا تنیس (`ATP` و `WTA`):**
   | تور (Tour) | جمتریا پایه (`egem`) | محاسبه درجه پایه | `DEG1` ثابت | موقعیت زودیاک | عنصر (Element) | تیکر Kalshi |
   | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
   | **ATP (مردان)** | `481` (`A=1 + T=400 + P=80`) | `481 - 360 = 121` | **`121`** | **`1° LEO`** (برج شیر / خانه ۴ از ۰) | **`FIRE`** | `KXATPMATCH` |
   | **WTA (زنان)** | `407` (`W=6 + T=400 + A=1`) | `407 - 360 = 47` | **`47`** | **`17° TAURUS`** (برج ثور / خانه ۱ از ۰) | **`EARTH`** | `KXWTAMATCH` |

3. **ایزولاسیون ۱۰۰٪ از شیت‌ها و سرویس‌های زنده NBA و NHL:**
   - متغیر `TENNIS_SHEETS_WRITE_ENABLED` به صورت پیش‌فرض `false` / `0` است.
   - هرگونه دسترسی یا نوشتن خودکار روی شیت‌های زنده `NBA-PLAYERS-GEOMANTIC-INPUT`، `NBA-FUSION-CALCULATION` و سایر شیت‌های NBA/NHL در لایه `_lib/sheets.py` مسدود شده است.
   - فایل وضعیت صرافی کالشی به `kalshi_tennis_state.json` ایزوله شده و در `.gitignore` قرار دارد.

---

## فایل‌های کلیدی کانفیگ تنیس (گام اول)

- [`tennis_config.py`](./artifacts/api-server/python/_lib/tennis_config.py) — ثابت‌های نجومی-جمتریا پایتون (`ATP_DEG1=121`, `WTA_DEG1=47`, `BIRTHDATE_USED=False`) و گارد ایزولاسیون شیت‌ها
- [`sheets.py`](./artifacts/api-server/python/_lib/sheets.py) — محافظ سخت‌افزاری عدم اتصال/نوشتن روی شیت‌های NBA و NHL
- [`tennis-config.ts`](./artifacts/api-server/src/lib/tennis-config.ts) — پروفایل‌های تایپ‌اسکریپت `ATP` و `WTA` و تیکرهای `KXATPMATCH` / `KXWTAMATCH`
- [`steps-config.ts`](./artifacts/api-server/src/lib/steps-config.ts) — تعریف گام‌های ایزوله پایپ‌لاین محاسباتی تنیس
- [`preset.ts`](./artifacts/api-server/src/routes/preset.ts) — سرویس API و دریافت بازارهای زنده `KXATPMATCH` و `KXWTAMATCH` از Kalshi
- [`App.tsx`](./artifacts/calc-dashboard/src/App.tsx) — رابط کاربری تمیز و سوییچر پروفایل `ATP (121 • 1° LEO)` / `WTA (47 • 17° TAURUS)`
