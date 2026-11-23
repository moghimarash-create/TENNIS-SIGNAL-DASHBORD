# TENNIS-SIGNAL-DASHBORD

**موتور پایه نجومی-جمتریا تنیس (ATP & WTA) — ۱۰۰٪ مبتنی بر جمتریا نام‌ها (`EnglishGem`) و آسمان روز و مکان تورنمنت (`pyswisseph`)**

> **قانون معماری قطعی:**  
> این سیستم ۱۰۰٪ **نجومی-جمتریا (Astro-Gematria)** است و **هیچ استفاده‌ای از تاریخ تولد بازیکنان نمی‌کند (`BIRTHDATE_USED = False`)**. همچنین به صورت ۱۰۰٪ ایزوله از مخازن و شیت‌های زنده `NBA-*` و `NHL-*` اجرا می‌شود.

---

## ۱. جدول جمتریا استاندارد (`EnglishGem`) و درجات پایه (`DEG1`)

| حروف | مقدار | حروف | مقدار |
| :--- | :---: | :--- | :---: |
| `A` | `1` | `L` | `30` |
| `B` | `2` | `M` | `40` |
| `G` | `3` | `N` | `50` |
| `D` | `4` | `S` | `60` |
| `E` | `5` | `O, X` | `70` |
| `U, V, W` | `6` | `F, P` | `80` |
| `Z` | `7` | `Q` | `100` |
| `H` | `8` | `R` | `200` |
| `I, J, Y` | `10` | `T` | `400` |
| `C, K` | `20` | سایر کاراکترها | `0` |

- **ATP (تور مردان):** `EnglishGem("ATP") = 481` ➔ `481 mod 360 = 121` ➔ **`DEG1 = 121` (`1° LEO` • عنصر `FIRE`)**
- **WTA (تور زنان):** `EnglishGem("WTA") = 407` ➔ `407 mod 360 = 47` ➔ **`DEG1 = 47` (`17° TAURUS` • عنصر `EARTH`)**

---

## ۲. سه آپشن قابل انتخاب `DEG3` در زاویه اول (`T`) + زاویه دوم (`P`)

- **`DEG2` (زاویه اول `T`):** `MOD(EnglishGem(Player_Full_Name), 360)`
- **سه آپشن `DEG3` در زاویه اول (`T`):**
  1. **`opt1` (`CITY_PLUS_TOURNAMENT`):** `MOD(EnglishGem(City), 360) + MOD(EnglishGem(Tournament), 360)`
  2. **`opt2` (`TOURNAMENT_ONLY`):** `MOD(EnglishGem(Tournament), 360)`
  3. **`opt3` (`CITY_ONLY` — پیش‌فرض برنده بنچمارک):** `MOD(EnglishGem(City), 360)`
- **زاویه دوم (`P` — تطابق فردی کورت و کد بازیکن):**
  - `DEG2 = MOD(EnglishGem(Player_Last_Name), 360)`
  - `DEG3 = MOD(EnglishGem(Surface), 360) + MOD(EnglishGem(Player_IOC_Code), 360)`

---

## ۳. خلاصه بنچمارک Zero-Lookahead سه فصل (`2024–2026` • `16,551` مسابقه انفرادی تور اصلی)

| آپشن زاویه | فرمول `DEG3` | دقت کل `F1` (`ATP+WTA`) | دقت قفل `VIP` (`ATP+WTA`) |
| :--- | :--- | :---: | :---: |
| **`opt3` (`CITY_ONLY` — پیش‌فرض)** | `MOD(EnglishGem(City), 360)` | **`61.16%`** (`1573/2572`) | **`66.42%`** (`1086/1635`) |
| **`opt1` (`CITY_PLUS_TOURNAMENT`)** | `MOD(EnglishGem(City), 360) + MOD(EnglishGem(Tournament), 360)` | `60.37%` (`1633/2705`) | `66.21%` (`1148/1734`) |
| **`opt2` (`TOURNAMENT_ONLY`)** | `MOD(EnglishGem(Tournament), 360)` | `60.33%` (`1592/2639`) | `66.03%` (`1098/1663`) |
| **زاویه دوم `P` (`SURFACE_IOC`)** | `MOD(EnglishGem(Surface), 360) + MOD(EnglishGem(IOC), 360)` | **`61.94%`** (`1644/2654`) | — |

---

## ۴. تست تطابق خودکار Python ↔ TypeScript

```bash
python3 artifacts/api-server/python/test_english_gem_parity.py
```
