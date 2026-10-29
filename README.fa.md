# نِت‌نما · NetNama

نمای روشن دامنه و شبکه؛ وب‌اپ فارسی/انگلیسی با Flask، بدون دیتابیس و سرویس پولی
اجباری. رابط راست‌به‌چپ/چپ‌به‌راست، تم روشن/تاریک/سیستم، خروجی زنده و دانلود
TXT، JSON و JSON.TXT دارد. همهٔ ابزارها از **سرور** اجرا می‌شوند.

[راهنمای انگلیسی](README.md) · [سند اصلی](.docs/NETNAMA_AGENT_SPEC_FA.md) ·
[گزارش آزمون](docs/VALIDATION.md) · [امنیت](SECURITY.md)

## اجرای محلی

Python نسخهٔ ۳٫۱۲ یا بالاتر لازم است. Node فقط برای بازسازی فایل‌های رابط لازم
است؛ نسخهٔ کامپایل‌شده، فونت‌های محلی و منابع رسمی همراه پروژه هستند.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --require-hashes -r requirements.lock
python -m pip install --no-deps -e .
python -m netnama
```

نشانی: **http://127.0.0.1:8080**؛ ورود اولیهٔ محلی: **admin / 123456**.
رمز را در «منابع و تنظیمات» تغییر دهید. برای پورت دیگر:
`python -m netnama --port 9090`.
روش جایگزین: `uv sync --locked` سپس `uv run python -m netnama`.

در PowerShell ویندوز:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --require-hashes -r requirements.lock
python -m pip install --no-deps -e .
python -m netnama
```

اگر فعال‌سازی محیط مجاز نیست، مستقیماً `.\.venv\Scripts\python.exe` را اجرا
کنید. در macOS پس از نصب Python ۳٫۱۲+ دستورهای لینوکس قابل استفاده‌اند. اجرای
بومی Windows/macOS در این محیط **تأیید نشده است**؛ CI سه‌سکویی تعریف شده و
تست ساخت آرگومان‌ها جای اجرای واقعی آن سیستم‌ها را نمی‌گیرد.

## قابلیت‌ها و معنای نتایج

- دامنه: ورودی چندخطی، TXT با UTF-8/BOM، ترکیب نام و پسوند، IDNA، فهرست TLD
  از IANA و تشخیص دامنهٔ قابل ثبت با PSL. زیردامنه با پیشنهاد دامنهٔ اصلی رد
  می‌شود و هیچ تبدیل یا استعلام پنهانی انجام نمی‌شود.
- استعلام مرجع RDAP از bootstrap رسمی IANA با longest suffix match؛ ‎`.ir`
  از adapter اختصاصی WHOIS در NIC.IR استفاده می‌کند. پاسخ ثبت‌شده باید با هدف
  منطبق باشد. تشخیص نبود رکورد ‎`.ir` تنها با عبارت دقیق مشاهده‌شده در پاسخ واقعی
  و نام هدف منطبق انجام می‌شود. پاسخ خالی، مبهم یا خطا «آزاد» نیست.
- DNS با dnspython، بخش‌های پاسخ/مرجع/اضافی، TTL و RCODE، رکوردهای متداول،
  resolver سیستم یا preset و TCP/UDP. خروجی dig-style است؛ ادعای اجرای native
  dig، ‎+trace یا اعتبارسنجی کامل رمزنگاری DNSSEC ندارد.
- Ping واقعی با برنامهٔ سیستم، ۱ تا ۱۰ بسته، سقف ۳۰ ثانیه و توقف subprocess
  با لغو. نبود ping، نبود مجوز ICMP و عدم پاسخ صادقانه نمایش داده می‌شوند.
  زمان انتظار Linux برابر ۲ ثانیه، macOS برابر ۲۰۰۰ میلی‌ثانیه و Windows برابر
  ۲۰۰۰ میلی‌ثانیه است. در macOS برای IPv6 از ping6 استفاده می‌شود.
- تشخیص IP، محاسبهٔ CIDR بدون شمردن آدرس‌های شبکهٔ بزرگ، PTR و IP RDAP.
  اطلاعات تخصیص IP بیانگر مکان دقیق یا مالک قطعی دستگاه نیست.
- سرآیندهای HTTP و گواهی TLS با اعتبارسنجی chain/hostname و SNI؛ فقط پورت‌های
  ۸۰/۴۴۳ و تغییرمسیر محدود. شکست اعتبارسنجی TLS موفق نشان داده نمی‌شود.

«احتمالاً آزاد» فقط یعنی رکورد ثبت در پاسخ معتبر مرجع پیدا نشد؛ خرید، قیمت،
Premium، رزرو و شرایط رجیستری تضمین نمی‌شود. نبود DNS و تاریخ انقضا به معنی
آزادشدن دامنه نیست. هیچ شماره و نتیجهٔ شبکهٔ ساختگی در محصول وجود ندارد.

## حریم داده و محدودیت‌ها

ورودی‌ها، نتایج، cache، نشست‌ها و rate limit فقط در RAM هستند. نتیجه پس از
۱۵ دقیقه منقضی می‌شود؛ restart همهٔ کارها و نشست‌ها را از بین می‌برد. فایل
ورودی روی دیسک ذخیره نمی‌شود و گزارش فقط با درخواست صریح دانلود می‌شود.
در localStorage فقط زبان و تم می‌مانند. اطلاعات تماس WHOIS خروجی داده نمی‌شود.

پوشهٔ داده با `NETNAMA_DATA_DIR` قابل تنظیم است؛ پیشفرض از platformdirs می‌آید.
در لینوکس معمولاً `~/.local/share/NetNama` است. زیرپوشهٔ `config/` تنظیمات و hash
رمز و secret، و `resources/` داده‌های مرجع و manifest را نگه می‌دارند. این پوشه
باید خصوصی باشد. در Windows مجوز ACL را به حساب سرویس و مدیران محدود کنید.
هیچ پوشهٔ نتایج یا تاریخچه‌ای خودکار ساخته نمی‌شود.

سقف‌ها: ۱ مگابایت ورودی، ۱۰۰۰ دامنهٔ یکتا، ۲ کار باز برای هر نشست، ۴ کار فعال
و ۸ کار منتظر در کل، ۸ عملیات شبکهٔ همزمان، ۲ عملیات برای هر مرجع با فاصلهٔ
شروع یک ثانیه، حداکثر ۲ تلاش مجدد موقت و cache ثبت ۶۰ ثانیه. Force fresh نرخ
مجاز را دور نمی‌زند. حافظهٔ نتایج/رویداد و تعداد کارهای نگه‌داری‌شده محدود است. متغیرهای
`NETNAMA_RESULT_TTL` و `NETNAMA_MAX_RAM_MB` زمان نگه‌داری و سقف پذیرش کار را
تنظیم می‌کنند؛ سقف دوم معادل محدودیت RSS کل پردازه نیست.
SSE تا ۸ اتصال کل و ۲ اتصال هر نشست، heartbeat، reconnect، replay/resync و
polling جایگزین دارد. سقف‌ها به معنی مجوز استعلام نامحدود از سرویس بیرونی نیستند.

برنامه **تک‌پردازه** است: از چند worker یا debug reloader استفاده نکنید.
Waitress با ۲۴ thread و scheduler بلندعمر اجرا می‌شود. GitHub Pages و هاست
استاتیک برای اجرای بک‌اند کافی نیستند.

## انتشار عمومی و Docker

متغیرها را در محیط تنظیم کنید؛ فایل `.env` خودکار خوانده نمی‌شود. رمز/hash
محیطی فقط در bootstrap اولیه اعمال می‌شود؛ بعداً رمز از پنل تغییر می‌کند.

```sh
export NETNAMA_MODE=public
export NETNAMA_HOST=0.0.0.0
export NETNAMA_PASSWORD='your-long-unique-password'
export NETNAMA_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export NETNAMA_HTTPS=true
python -m netnama
```

حالت عمومی با رمز پیشفرض، secret ضعیف یا مجوز مقصد خصوصی شروع نمی‌شود. پشت
reverse proxy دارای HTTPS قرار دهید؛ `NETNAMA_HTTPS=true` را برای کوکی Secure
فعال کنید. پیشفرض هیچ forwarded header مورد اعتماد نیست. اگر ProxyFix اضافه
می‌کنید تعداد hop دقیق و مسیر دسترسی مستقیم به بک‌اند را کنترل کنید. برای SSE
buffering پراکسی خاموش و timeout بیش از ۷۵ ثانیه باشد. access log نباید هدف،
query، توکن یا secret را ثبت کند.

تمام IPهای حاصل از resolve بررسی می‌شوند. مقصد خصوصی، metadata، loopback،
link-local، multicast و IPv4-mapped IPv6 در حالت عمومی مسدود هستند. HTTP/TLS
به IP بررسی‌شده وصل می‌شوند و Host/SNI اصلی حفظ می‌شود؛ هر redirect دوباره
بررسی می‌شود. فقط برای آزمایش محلی مقصد خصوصی می‌توان
`NETNAMA_ALLOW_PRIVATE_TARGETS=true` گذاشت؛ هشدار در پنل نمایش داده می‌شود.

Docker: پس از تنظیم `NETNAMA_PASSWORD` و `NETNAMA_SECRET_KEY`، دستور
`docker compose up --build` را اجرا کنید. پورت میزبان فقط روی loopback منتشر
می‌شود. container با کاربر non-root، filesystem فقط‌خواندنی، volume قابل نوشتن
برای داده و بدون capability اجرا می‌شود. image حداقلی ping ندارد و این قابلیت
را unavailable نشان می‌دهد؛ در صورت نیاز، در image مشتق‌شدهٔ بررسی‌شده binary
و حداقل مجوز لازم را اضافه کنید. privileged ممنوع است. نتایج از شبکهٔ container
هستند. وضعیت تأیید واقعی Docker در گزارش آزمون ثبت شده است.

## منابع و توسعه

### نسخه‌بندی

نسخهٔ فعلی **v1.0.0** است. منبع اصلی نسخه
[`netnama/_version.py`](netnama/_version.py) است؛ بستهٔ پایتون، رابط کاربری،
API قابلیت‌ها و گزارش‌های خروجی همگی از همین مقدار استفاده می‌کنند.
قاعدهٔ `MAJOR.MINOR.PATCH`: تغییر ناسازگار، قابلیت جدید سازگار، و رفع اشکال.
برای انتشار بعدی، مقدار `__version__` را تغییر دهید، نسخهٔ فرانت‌اند را با
`npm version X.Y.Z --no-git-tag-version` هماهنگ کنید، `uv lock` و
`npm run build` را اجرا و تغییرات را در [CHANGELOG.md](CHANGELOG.md) ثبت کنید.
پس از بررسی و commit، تگ انتشار به‌شکل `vX.Y.Z` ساخته می‌شود.

پس از تغییر کد یا اجرای `npm run build`، فرایند NetNama را متوقف و دوباره اجرا
کنید و سپس صفحهٔ مرورگر را بازخوانی کنید. Waitress کد پایتون، قالب‌های کش‌شده و
ترجمه‌ها را خودکار بارگذاری مجدد نمی‌کند؛ ادامهٔ اجرای نسخهٔ قبلی می‌تواند HTML
قدیمی را با CSS و JavaScript جدید ترکیب و رابط را مختل کند. راه‌اندازی مجدد،
کارها و نشست‌های موجود در حافظه را پاک می‌کند.

به‌روزرسانی RDAP DNS/IPv4/IPv6، TLD و PSL تنها با دکمهٔ دستی انجام می‌شود.
ETag/Last-Modified، اعتبارسنجی schema، file lock، جایگزینی اتمیک و نسخهٔ قبلی
سالم استفاده می‌شوند. شکست یک منبع نسخهٔ قبلی را خراب نمی‌کند. منابع قدیمی
badge دارند و هر کار snapshot منابع زمان شروع خود را نگه می‌دارد. provenance
و hash منابع همراه در manifest موجود است. صفحهٔ شرایط NIC.IR هنگام بررسی
HTTP 403 داد؛ پیش از انتشار عمومی گروهی شرایط جاری سرویس را مستقلاً بررسی کنید.

```sh
uv sync --locked --extra dev
npm ci
npm run build
uv run pytest -q
uv run ruff check netnama tests
uv run ruff format --check netnama tests
uv run pip-audit -r requirements.lock --disable-pip
npm audit
# آزمایش واقعی کم‌تعداد و اختیاری:
uv run python scripts/live_smoke.py
```

فونت‌ها و مجوزهای آن‌ها محلی هستند؛ آیکون‌ها فقط با named imports انتخاب‌شده
bundle می‌شوند. Node هنگام اجرای محصول لازم نیست. کد اصلی MIT، فونت‌ها OFL و
PSL دارای MPL 2.0 است؛ [مجوزهای ثالث](THIRD_PARTY_NOTICES.md) را ببینید.
