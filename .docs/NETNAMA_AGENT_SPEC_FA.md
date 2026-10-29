# NetNama | نِت‌نما — سند اجرایی توسعه برای Agentها

نسخه: 1.0 • تاریخ: 2026-10-29 • نوع تحویل: مشخصات اجرایی، نه برنامه پیاده‌سازی‌شده

> دستور اصلی به Agent: این سند مرجع محصول و معیار تحویل است. یک برنامه واقعی و قابل اجرا بساز؛ هیچ ابزار شبکه‌ای نباید با داده ساختگی موفقیت نشان دهد. وضعیت نامشخص را صادقانه نمایش بده. تصمیم‌های معماری زیر را بدون دلیل مستند تغییر نده. تمام مراحل اجرایی را در CHECKLIST.md ثبت کن.

## 1. هویت محصول

نام: **NetNama / نِت‌نما**. مفهوم: نمای روشن از دامنه و شبکه. شعار فارسی: «نمای روشن دامنه و شبکه». شعار انگلیسی: “Clarity for domains and networks.” شناسه پیشنهادی مخزن: `netnama`؛ پکیج پایتون داخلی: `netnama`. این نام پیشنهادی است و آزاد بودن دامنه، نام مخزن و علامت تجاری آن بررسی نشده است؛ هیچ ادعای مالکیت یا در دسترس بودن نساز.

لوگو: نشانه برداری N با سه گره، اشاره به شبکه و مسیر استعلام. فایل‌های assets/logo.svg و assets/logo-mono.svg همراه سند مرجع هستند. SVG را مستقیماً استفاده کن، با CSS رنگ بده و favicon را از همان هندسه تولید کن. نشانه باید در 20 تا 24 پیکسل خوانا باشد؛ لوگوی جدید رستری یا تصویر سنگین لازم نیست. نام برند را کنار SVG به‌صورت متن واقعی بنویس.

## 2. هدف و حدود

یک وب‌اپ سبک متن‌باز با ظاهر پنل مدیریت برای بررسی گروهی دامنه و ابزارهای دامنه/IP. زبان کامل فارسی و انگلیسی، RTL/LTR، دارک/لایت، خروجی زنده ترمینال‌مانند، فایل ورودی TXT و خروجی TXT/JSON. Linux اولویت اول؛ اجرای بومی Windows و macOS نیز مستند و آزموده شود. تمام ابزارها از بک‌اند اجرا می‌شوند؛ Ping اندازه‌گیری مسیر **سرور تا مقصد** است، نه کامپیوتر کاربر تا مقصد.

بدون دیتابیس: نه SQLite، نه ORM، نه Redis، نه سرویس خارجی اجباری. بدون ثبت تاریخچه دائمی نتایج، بدون آپلود دائمی فایل و بدون ذخیره خودکار هدف‌های بررسی. نتیجه‌های جاری فقط در RAM با TTL هستند. تنظیمات و منابع مرجع در فایل نگهداری می‌شوند. دانلود گزارش با درخواست صریح کاربر انجام می‌شود. restart کارهای جاری را از بین می‌برد؛ آن را در مستندات روشن کن.

خرید دامنه، انتقال دامنه، مدیریت DNS ارائه‌دهندگان، پورت‌اسکن، اجرای shell دلخواه، مانیتورینگ دائمی، GeoIP پولی و حساب چندکاربره خارج از دامنه نسخه اول هستند.

## 3. تصمیم فنی قطعی

**Flask + Jinja2 + Tailwind CSS + JavaScript ماژولار + Lucide**.

Flask به دلیل نداشتن مدل داده، ORM و نیاز به Django Admin انتخاب می‌شود. پنل کاملاً سفارشی است. ساختار factory و Blueprint الزامی است؛ هسته ابزارها از HTTP مستقل بماند. استفاده از Django، React، Next.js، SPA framework و FastAPI برای این نسخه لازم نیست.

پایه Python 3.12+؛ هنگام اجرا سازگاری نسخه‌ها را بررسی و نسخه دقیق وابستگی‌ها را قفل کن. Python packages: Flask، Flask-WTF برای CSRF، httpx، dnspython، idna، publicsuffix2 یا معادل دارای API برای بارگذاری PSL محلی، platformdirs، filelock، waitress. توسعه: pytest، Ruff، pip-audit. هر وابستگی اضافه باید دلیل داشته باشد؛ requests و httpx را همزمان برای یک کار نصب نکن.

Frontend build: `tailwindcss`, `@tailwindcss/cli`, `lucide`, `esbuild`؛ npm lockfile. Node فقط build-time. Tailwind را compile/minify کن، CDN و Play CDN در محصول ممنوع. Lucide فقط named imports آیکون‌های استفاده‌شده؛ bundle کل کتابخانه ممنوع. فونت‌ها local WOFF2 با مجوزهای همراه؛ فارسی Vazirmatn از خانواده وزیر، انگلیسی Inter، ترمینال JetBrains Mono با fallback monospace. فونت فارسی فقط برای متن رابط؛ دامنه و خروجی فنی LTR.

WSGI: Waitress یک process با threadهای محدود برای هر سه سیستم‌عامل. کارها در scheduler بلندعمر در سطح process اجرا شوند، نه asyncio.create_task داخل view Flask. یک scheduler با event loop اختصاصی در thread جدا و یک httpx.AsyncClient مشترک، به‌علاوه executor محدود برای subprocess/عملیات blocking. loop و client هنگام shutdown بسته شوند. ظرفیت ورودی با semaphore/صف bounded کنترل شود؛ ThreadPoolExecutor به‌تنهایی صف bounded فراهم نمی‌کند.

نسخه اول **single-process** است. اجرای چند worker بدون state مشترک پشتیبانی نمی‌شود. debug reloader نباید scheduler را دو بار بسازد. Redis/Celery برای پنهان کردن این محدودیت اضافه نکن.

## 4. صفحات و اطلاعات معماری

- ورود: برند، فرم کوتاه، تغییر زبان/تم، نمایش خطای عمومی و حالت submitting.
- نمای کلی: کارت ابزارها، تعداد وضعیت‌های کار جاری، سلامت قابلیت‌های همین سرور؛ شمارنده ساختگی یا تاریخچه دائمی ممنوع.
- بررسی گروهی دامنه: paste، TXT، ترکیب نام پایه و پسوند، جدول و خروجی.
- DNS / Dig: ورودی دامنه، نوع رکورد، resolver و terminal.
- Ping: هدف، تعداد محدود، terminal و آمار.
- ابزار IP: اعتبارسنجی، PTR، RDAP، CIDR.
- HTTP / TLS: تشخیص پاسخ و گواهی با تنظیمات محدود.
- منابع و تنظیمات: نسخه منابع، به‌روزرسانی دستی، توانایی سرور، تنظیم نمایش.
- درباره: نسخه، مجوز، محدودیت‌ها و لینک منابع رسمی.

Desktop: sidebar حدود 248px، topbar، breadcrumb کوتاه، عنوان و توضیح یک‌خطی، toolbar و workspace. در فارسی sidebar سمت راست؛ در انگلیسی چپ. Mobile: drawer، فرم تک‌ستونی و نتایج کارت یا جدول scroll افقی. viewportهای 360، 768، 1280، 1920 بررسی شوند.

## 5. سیستم طراحی

حس بصری: ابزار حرفه‌ای شبکه، خلوت، تایپوگرافی دقیق، سطح‌های نرم و تاکید فیروزه‌ای؛ نه نمودارهای تزئینی و انیمیشن‌های سنگین.

Dark tokens: background #0B1120، surface #111B2E، raised #18243B، border #2B3A54، text #E8EEF7، muted #A5B4C9، accent #2DD4BF.
Light tokens: background #F4F7FB، surface #FFFFFF، raised #EAF0F7، border #CBD5E1، text #142033، muted #52627A، accent #0F766E.

Statusها: موفق سبز، مشکوک/احتمالی کهربایی، خطا قرمز، pending آبی خاکستری. رنگ به تنهایی معنی را نرساند؛ label و icon اضافه کن. contrast WCAG AA، focus واضح، کلیدهای حداقل 40px، radius حدود 12 تا 16px، shadow محدود، spacing براساس 4px.

Theme: light/dark/system؛ در اولین paint با اسکریپت کوچک و CSP سازگار اعمال شود تا flash رخ ندهد. فقط theme و locale می‌توانند در localStorage بمانند؛ نتیجه یا دامنه حساس را آنجا ذخیره نکن. از CSS logical properties مثل padding-inline و start/end استفاده کن.

Loading: skeleton فقط برای ساختار اولیه، spinner روی عمل فعال، نوار پیشرفت با تعداد تکمیل‌شده/کل. درصد ساختگی ممنوع؛ در زمان نامعلوم حالت indeterminate. کنترل لغو فعال بماند. empty/error/partial/cancelled/reconnecting state طراحی شود. motion کوتاه 120 تا 180ms و احترام به prefers-reduced-motion. overlay تمام‌صفحه در هر استعلام ممنوع.

## 6. دو زبان و دسترس‌پذیری

تمام labelها، tooltip، validation، loading، خطا، status و گزارش متنی با کلید ترجمه. `locales/fa.json` و `locales/en.json` با تست برابری کلیدها؛ قالب‌بندی سمت سرور و JS از یک catalog استفاده کند. متن فارسی در JS hardcode نشود. HTML lang/dir صحیح؛ زبان پیشفرض fa، انتخاب کاربر پایدار. اعداد دامنه/IP/زمان فنی ASCII؛ زمان نمایش محلی با timezone مرورگر، export با UTC ISO-8601.

از bdi و dir=ltr برای domain/IP/path، و pre با جهت LTR استفاده کن. keyboard navigation، aria-label دوزبانه، aria-live polite برای خلاصه رویدادها، نه خواندن تک‌تک خطوط Ping. focus trap و Escape برای dialog/drawer. پس از تغییر زبان داده و job جاری از دست نرود.

## 7. ورود و نشست بدون دیتابیس

طبق درخواست محصول، ورود پیشفرض `admin` / `123456` در حالت local توسعه کار کند. مشخصات در config/bootstrap تعریف شوند؛ بعد از bootstrap در فایل تنظیمات فقط password hash استاندارد Werkzeug نگهداری شود، نه plaintext. نام کاربری با env قابل override؛ رمز/hash و secret از repository و export حذف شوند.

حالت local به طور پیشفرض فقط 127.0.0.1 گوش دهد. حالت public با env صریح فعال شود؛ برای public باید رمز پیشفرض عوض شود و SECRET_KEY قوی باشد؛ در غیراینصورت startup با پیام روشن متوقف شود. این امر مانع استفاده محلی با اطلاعات درخواستی نیست.

نشست signed cookie کوتاه‌عمر فقط شناسه تصادفی session و auth_version داشته باشد؛ هیچ password یا نتیجه در cookie نباشد. سرور sessionهای فعال را در RAM با TTL نگه دارد، logout آن را ابطال کند، restart خروج از حساب ایجاد کند. HttpOnly، SameSite=Lax و Secure در HTTPS. CSRF روی login و تمام mutationها. rate limit ورود در RAM، پیام خطای عمومی، مقایسه hash. تغییر رمز در تنظیمات فایل را اتمیک عوض کند، auth_version را تغییر دهد و نشست‌ها را باطل کند.

تمام APIها، SSE، export و updater احراز هویت و مالکیت job می‌خواهند. debug خاموش در production، secret در log ممنوع. نشست demo عمومی یا ورود خودکار ممنوع.

## 8. هسته بررسی دامنه

### 8.1 ورودی

paste چندخطی، فایل UTF-8/UTF-8-BOM TXT با هر خط یک دامنه، پشتیبانی CRLF، خطوط خالی و comment با #. سقف پیشنهادی 1 MiB و 1000 دامنه یکتا در job. فایل را stream parse کن، روی دیسک نگه ندار. slash، credentials، port و URL کامل در ورودی دامنه را با خطای واضح رد کن؛ پاکسازی مبهم و تبدیل خاموش انجام نده. lowercase، trim، حذف یک نقطه انتهایی، IDNA UTS46 معتبر و حفظ unicode/A-label. موارد تکراری فقط یکبار استعلام، ولی mapping خطوط ورودی برای گزارش موجود باشد.

TLD موجود در فهرست IANA را با suffix قابل ثبت اشتباه نگیر. PSL برای تشخیص ساختارهایی مثل co.uk استفاده شود؛ آن سند eligibility ثبت نیست. subdomain را آزاد اعلام نکن؛ اگر دامنه ثبت‌پذیر متفاوت است پیشنهاد بده و با اطلاع کاربر همان را بررسی کن. پسوند ناشناخته invalid/unsupported، نه available.

generator: چند نام پایه × چند پسوند با پیش‌نمایش تعداد، حذف تکراری و همان سقف. دامنه‌های IDN تابع محدودیت رجیستری هستند؛ صحت نحوی تضمین پذیرش ثبت نیست.

### 8.2 کشف مرجع

منبع bootstrap: https://data.iana.org/rdap/dns.json
سرور authoritative را طبق RFC 9224 و longest suffix match پیدا کن. آدرس‌ها hardcode عمومی نشوند. نمونه‌ها: `.com` پایه https://rdap.verisign.com/com/v1/ و `.net` پایه https://rdap.verisign.com/net/v1/؛ استعلام `{base}domain/{ascii_domain}` طبق RFC 9082. `Accept: application/rdap+json`، TLS validation روشن و timeout الزامی.

برای `.ir` مطابق اطلاعات فعلی IANA، WHOIS در `whois.nic.ir:43` با ارسال `{ascii_domain}\r\n`؛ RDAP عمومی در IANA درج نشده است. adapter جدا با fixture برای پاسخ ثبت‌شده، no-match واقعی، rate-limit، متن مبهم و timeout. ابتدا پاسخ‌های واقعی و شرایط سرویس را بررسی کن؛ regex حدسی برای آزاد بودن ننویس. پاسخ خالی یا خطا آزاد نیست. برای دیگر ccTLDها adapter ثبت‌شده و قابل آزمون؛ یک parser واحد WHOIS برای تمام جهان ممنوع. نبود adapter = unsupported. هرگز همهٔ WHOISها را به whois.nic.ir نفرست.

### 8.3 طبقه‌بندی قابل اتکا

- registered: پاسخ معتبر authoritative حاوی domain object منطبق با هدف.
- likely_available: پاسخ معتبر RDAP «پیدا نشد» از endpoint صحیح، یا no-match صریح و شناخته‌شده WHOIS؛ این عنوان یعنی فاقد رکورد، نه تضمین خرید.
- available_at_registrar: فقط پاسخ صریح API ثبت‌کننده؛ نام provider و زمان الزامی.
- unavailable: رزرو/مسدود/غیرقابل ثبت فقط با شاهد صریح منبع مناسب.
- invalid، unsupported، unknown، rate_limited، error، cancelled جدا باشند.

HTTP 404 HTML عمومی، endpoint غلط، 403، 429، 5xx، timeout، پاسخ نامعتبر یا نبود DNS => آزاد نیست. objectClassName و نام دامنه را validate کن. دامنه رزروشده، Premium، eligibility، دوره حذف و شرایط ثبت می‌توانند مانع خرید باشند. تاریخ انقضا را زمان آزاد شدن تعبیر نکن.

نتیجه: نام ورودی، Unicode، ASCII، status، reason_code، explanation_key، source، checked_at، duration_ms، cached، attempts و evidence حداقلی. داده تماس شخصی WHOIS به‌صورت پیشفرض در UI/export نیاید؛ raw output فقط با انتخاب کاربر و بدون secrets.

### 8.4 concurrency

پیشفرض 8 کار شبکه همزمان در کل و حداکثر 2 برای یک authority؛ شروع محافظه‌کارانه 1 request/second برای هر host، با پیکربندی پایین‌تر مطابق سیاست سرویس. این مقادیر تضمین پذیرش رجیستری نیستند. authority مشترک بین پسوندها یک limiter مشترک داشته باشد. Retry-After، backoff نمایی با jitter و حداکثر 2 retry برای خطاهای موقت؛ input نامعتبر retry نشود. timeout اتصال 5s و read 10s با سقف زمانی کل هر هدف. cache نتیجه فقط RAM با TTL حدود 60s و گزینه Force fresh؛ limiter با force دور زده نشود. throughput واقعی در benchmark گزارش شود؛ ادعای هزار دامنه در چند ثانیه ممنوع.

Registrar adapters در معماری interface داشته باشند، ولی نسخه پایه بدون کلید کار کند. Namecheap یا دیگر providerها افزونه اختیاری با تنظیمات واقعی و تست جدا هستند؛ Sandbox را به عنوان استعلام واقعی نمایش نده. هیچ API پولی/نامحدود فرض نشود.

## 9. DNS / Dig

پیاده‌سازی اصلی با dnspython برای برابری سیستم‌عامل‌ها؛ نصب باینری dig شرط کارکرد نیست. رابط «DNS / Dig» توضیح دهد خروجی قالب dig-style است و الزاماً فرمان native dig نیست.

انواع: A، AAAA، CNAME، MX، NS، TXT، SOA، CAA، SRV، PTR؛ برای SRV نام سرویس با underscore معتبر است و validator جدا از دامنه قابل ثبت می‌خواهد. پرسش DNS با ورودی ثبت دامنه یکی نیست. apex و FQDN حفظ شوند.

resolver: system، presetهای قابل تنظیم مثل 1.1.1.1 و 8.8.8.8، و custom resolver فقط در local mode یا allowlist تنظیمات. نتیجه structured شامل question، answer، authority، additional، TTL، RCODE، query time، resolver و transport. NXDOMAIN، NOERROR بدون answer، SERVFAIL، timeout و refusal تفکیک شوند. UDP با fallback TCP در truncation. محدودیت اندازه/زمان. قابلیت TCP اختیاری. DNSSEC flag را با «اعتبارسنجی رمزنگاری‌شده DNSSEC» اشتباه نگیر؛ validation کامل بدون پیاده‌سازی واقعی ادعا نشود. نسخه اول dig +trace واقعی ندارد؛ NS lookup را trace ننام.

## 10. Ping

ICMP واقعی با binary سیستم‌عامل و subprocess بدون shell. ابزار پیش از اجرا قابلیت سرور را کشف کند. Linux/macOS/Windows argument builder جدا با timeout و تعداد: 1 تا 10، پیشفرض 4. Linux معمولاً `-c` و Windows `-n` است؛ semantics زمان انتظار هر پلتفرم را مستقل مستند و تست کن، فرمان Linux را در macOS کپی نکن.

shell=False، آرگومان‌ها لیست، target resolve شده و validated؛ IPv4/IPv6 و گزینه‌های مناسب هر سیستم. deadline نهایی 30s، cancellation و kill/wait و بستن pipe. stdout/stderr با encoding پلتفرم decode شوند. raw output به شکل textContent، نه innerHTML. parsing summary ترجیحاً از آمار پایدار؛ اگر locale/فرمت ناشناخته بود raw نتیجه و summary unavailable نشان بده، عدد ساختگی نساز.

نبود binary، ICMP permission، مسدود بودن ICMP و packet loss جدا نمایش داده شود؛ عدم پاسخ Ping به معنی down بودن وب‌سایت یا آزاد بودن دامنه نیست. Docker Linux ممکن است capability محدود NET_RAW برای ping بخواهد؛ privileged container ممنوع. fallback TCP latency تنها با عنوان صریح «TCP probe» و نه ICMP Ping، روی پورت‌های allowlist 80/443 و تعداد محدود؛ این قابلیت پورت‌اسکن نیست.

## 11. سایر قابلیت‌های الزامی

1. IP inspector: IPv4/IPv6 normalization، public/private/loopback/link-local/multicast/reserved و خانواده با ipaddress؛ بدون درخواست شبکه.
2. Reverse DNS: PTR و forward-confirmed reverse DNS اختیاری با گزارش جدا، نه اثبات مالکیت.
3. IP RDAP: کشف RIR با bootstrap IPv4/IPv6 و longest prefix match؛ نمایش محدوده تخصیص/سازمان/منبع، نه موقعیت دقیق جغرافیایی یا مالک قطعی دستگاه.
4. CIDR calculator: network، prefix، netmask، range، اندازه شبکه با ipaddress؛ IPv6 بزرگ را enumerate نکن. محاسبه تعداد آدرس و usable تابع خانواده و prefix، /31 و /32 درست تفسیر شوند.
5. HTTP headers: GET محدود و streaming بدون دانلود body کامل، وضعیت، selected headers، redirect chain حداکثر 5، زمان‌ها. ports فقط 80/443؛ بدون arbitrary method/body، cookie کاربر یا credentials. HEAD fallback به GET با body cap و توضیح. body cap 64KiB، timeout حدود 10s.
6. TLS certificate: اتصال TLS استاندارد به hostname روی 443، SNI، اعتبار chain/hostname، issuer، SAN، notBefore/notAfter، days remaining و negotiated protocol. TLS failure موفق نمایش داده نشود؛ حالت بررسی insecure اگر اضافه شد جدا و واضح باشد و پیشفرض خاموش.
7. Domain helpers: Unicode/Punycode converter، دامنه قابل ثبت، فهرست suffixهای مجاز، تولید ترکیب نام/پسوند.

Traceroute و native dig می‌توانند مرحله بعد باشند؛ در UI ابزار ناقص را فعال و mock نکن. هیچ GeoIP API اجباری نیست.

## 12. کنترل مقصد و اجرای شبکه

چون وب‌اپ دارای HTTP/TLS/Ping است، حفاظت از درخواست به شبکه داخلی جزو خود پیاده‌سازی است. public mode هدف‌های غیر public شامل loopback، private، link-local، multicast، metadata و IPv4-mapped IPv6 ممنوع. پس از resolve تمام آدرس‌ها ارزیابی شوند؛ اگر هر آدرس ممنوع بود هدف رد شود. فقط اعتبارسنجی string قبل از DNS کافی نیست.

HTTP و TLS به IP بررسی‌شده وصل شوند، ولی hostname اصلی برای Host/SNI و verification حفظ شود؛ DNS rebind بین validation و connect رخ ندهد. هر redirect دوباره validate، credentials از URL رد، scheme فقط http/https. resolver سفارشی دلخواه در public ممنوع. RDAP endpointها فقط از منابع معتبر validated با بررسی مقصد و redirect؛ کاربر نتواند base URL بدهد. WHOIS serverها از registry adapters معتبر، نه input کاربر.

local mode امکان allow_private_targets با هشدار محل اجرای درخواست داشته باشد؛ public mode آن را نادیده نگیرد، بلکه startup را در تنظیم ناامن رد کند. payloadها و خروجی‌های خارجی untrusted هستند؛ HTML escape، محدودیت حجم پاسخ، حذف ANSI/کنترل‌های مخرب و ممنوعیت shell. کاربر دستور دلخواه وارد نمی‌کند؛ فقط پارامتر ابزارهای مشخص.

## 13. ترمینال و فایل خروجی

ترمینال یک renderer رویداد است، نه shell تعاملی. header شامل ابزار/هدف/وضعیت، body monospace LTR، timestamp اختیاری، auto-scroll با توقف هنگام scroll کاربر، copy، clear view، cancel، wrap toggle و export. clear فقط نمایش را پاک کند و اثرش روی job روشن باشد. رندر batch با requestAnimationFrame؛ حداکثر 2000 خط و 1MiB با علامت truncation؛ لیست بی‌نهایت DOM ممنوع.

قالب‌ها: `.json`، `.txt` و بنا به درخواست کاربر `.json.txt`؛ آخری **همان JSON معتبر UTF-8** با پسوند مرکب است، نه JSON چسبانده‌شده به متن ترمینال. export JSON با ensure_ascii=False و schema_version. TXT قابل خواندن شامل همه ورودی‌ها، وضعیت‌ها، خطاها و summary. فایل‌های export هرگز روی سرور به‌طور دائمی ذخیره نشوند؛ stream از snapshot نتیجه. برای export مرورگر با Blob و برای API با Content-Disposition attachment. نام امن مثل netnama-dns-20261029T103000Z.json.txt.

ساختار استاندارد نمونه:

```json
{
  "schema_version": "1.0",
  "app": {"name": "NetNama", "version": "0.1.0"},
  "tool": "domain_batch",
  "job_id": "opaque-random-id",
  "started_at": "2026-10-29T10:30:00Z",
  "finished_at": null,
  "execution_origin": "server",
  "status": "running",
  "parameters": {"force_fresh": false},
  "sources": [],
  "summary": {"total": 1, "completed": 0},
  "results": [],
  "events": [],
  "truncated": false
}
```

enumها و reason_code زبان‌خنثی، locale جدا و labelهای ترجمه‌شده اختیاری. export بدون رمز، session id، CSRF، secret یا API key. خروجی در حال اجرا partial و cancelled را حفظ کند؛ هنگام export وضعیت snapshot و زمان آن ثبت شود.

## 14. jobها، API و SSE

contract:
- POST /auth/login؛ POST /auth/logout؛ POST /auth/password
- GET /api/capabilities
- POST /api/jobs با tool/targets/options validated
- GET /api/jobs/{id} برای snapshot و polling fallback
- GET /api/jobs/{id}/events برای SSE
- POST /api/jobs/{id}/cancel
- GET /api/jobs/{id}/export?format=json|txt|json.txt
- GET /api/resources
- POST /api/resources/update با resource id از allowlist

status: queued → running → completed|partial|failed|cancelled. cancel idempotent؛ نتیجه تکمیل‌شده بازنویسی نشود. سقف 2 job فعال برای هر session، 4 کل برنامه، صف حداکثر 8، retention نتیجه 15 دقیقه و سقف RAM قابل تنظیم. حافظه کلی و حافظه هر job سقف داشته باشند؛ job جدید در فشار حافظه رد شود، نه OOM. job منقضی 410، ناموجود/غیرمجاز 404، validation 422، capacity/rate 429 با Retry-After، auth 401.

SSE: event id افزایشی، نوع state/result/line/progress/error/done، data JSON؛ ring buffer محدود برای reconnect با Last-Event-ID. اگر رویدادها حذف شده‌اند snapshot/re-sync event بفرست. heartbeat هر حدود 15s، Cache-Control no-cache، proxy buffering خاموش. stream خواننده job است، اجرا را آغاز نکند. چند tab نباید استعلام تکراری بسازند. disconnect نباید job را خودکار حذف کند؛ TTL و cancel کنترل می‌کنند. سقف connection همزمان و threadهای Waitress با ظرفیت job/SSE تنظیم شوند؛ stream بی‌نهایت workerها را اشغال نکند. timeout عمر stream و reconnect داشته باشد.

## 15. به‌روزرسانی دستی منابع

صفحه منابع و یک دکمه «به‌روزرسانی منابع / Update resources» با گزینه انتخاب هر منبع. به‌روزرسانی خودکار دوره‌ای وجود نداشته باشد. نمایش: آخرین تلاش، آخرین موفقیت، نسخه/تاریخ انتشار منبع، وضعیت و خطای واضح.

منابع allowlist:
- RDAP DNS: https://data.iana.org/rdap/dns.json
- RDAP IPv4: https://data.iana.org/rdap/ipv4.json
- RDAP IPv6: https://data.iana.org/rdap/ipv6.json
- TLD list: https://data.iana.org/TLD/tlds-alpha-by-domain.txt
- PSL: https://publicsuffix.org/list/public_suffix_list.dat

برای sourceهای مختلف fetch مستقل، timeout و size cap، HTTPS، ETag/Last-Modified و 304. ابتدا دانلود به فایل موقت همان filesystem، parse و schema/sanity validation، سپس file lock و atomic replace. شکست یک منبع نباید قبلی را خراب کند یا بقیه را موفق جلوه دهد. manifest با hash، publication، retrieved_at و status؛ previous good copy برای rollback. jobهای فعال snapshot منابع زمان شروع را نگه دارند. URL updater از کاربر گرفته نشود. دکمه update CSS/فونت/پکیج نصب نکند و shell اجرا نکند.

نسخه bundled معتبر با تاریخ و provenance برای اولین اجرا همراه release باشد؛ runtime از آن استفاده می‌کند تا اولین update دستی. منبع منقضی یا قدیمی با badge روشن، نه قطع بی‌دلیل برنامه. قبل release نسخه bundled را تازه و مجوز/notice را همراه کن. نبود منبع معتبر ابزار مربوط را unavailable کند؛ endpoint حدسی نساز.

## 16. فایل‌ها و حریم داده

مسیر قابل تنظیم NETNAMA_DATA_DIR با پیشفرض platformdirs.user_data_dir. پوشه‌ها: config/، resources/، tmp/. config و manifest با locking و atomic replace، permissions محدود در Linux/macOS و راهنمای ACL در Windows. repo فقط example config، هرگز secret و runtime data.

نتایج job و ورودی کاربر RAM، export سمت کاربر. tmp صرفاً برای updater و فایل ناقص؛ cleanup بعد شکست و startup. هیچ فایل results/history خودکار ساخته نشود. گزارش عملیاتی به stderr بدون target، query، محتوای فایل یا secret؛ URL querystring export در access log sanitise شود. فایل عملیاتی اختیاری، غیرفعال به پیشفرض و با rotation؛ با «عدم ذخیره نتیجه» تضاد نداشته باشد. ترجیحات theme/locale در مرورگر مجاز؛ config منابع و رمز دائمی مطابق نیاز برنامه است.

## 17. ساختار پیشنهادی مخزن

```text
netnama/
  __init__.py           # factory
  config.py
  auth/
  web/
  api/
  core/
    jobs.py
    scheduler.py
    events.py
    limits.py
    export.py
    validation.py
    target_policy.py
  tools/
    domain.py
    dns.py
    ping.py
    ip.py
    http.py
    tls.py
  providers/
    rdap.py
    whois_ir.py
    registrar_base.py
  resources/
    manager.py
    bundled/
  templates/
  static/dist/
  locales/fa.json
  locales/en.json
frontend/
  app.js
  terminal.js
  input.css
  icons.js
assets/brand/
tests/unit/
tests/integration/
tests/fixtures/
docs/
pyproject.toml
package.json
package-lock.json
Dockerfile
compose.yaml
.env.example
README.md
README.fa.md
LICENSE
THIRD_PARTY_NOTICES.md
SECURITY.md
CONTRIBUTING.md
CHECKLIST.md
```

## 18. اجرای چندسکویی و انتشار

یک entrypoint مثل `python -m netnama` با host/port مشخص، و production runner از Waitress. command نهایی پس از پیاده‌سازی در README واقعی ثبت شود. installer محیط مجازی Python را توضیح دهد. assets کامپایل‌شده در release باشند تا کاربر برای اجرا نیاز به Node نداشته باشد. ساخت release با npm ci و build تکرارپذیر؛ وابستگی‌های Python نیز reproducible lock مناسب داشته باشند.

Docker Linux non-root با data directory writable، healthcheck بدون افشای اطلاعات، graceful shutdown و عدم privileged. network/ping capability تشخیص داده شود؛ نبود آن بقیه برنامه را از کار نیندازد. Windows/macOS اجرای Python بومی؛ Docker روی این سیستم‌ها مسیر شبکه متفاوت دارد و نتایج از container هستند. پشت reverse proxy HTTPS، Trust proxy فقط با تعداد hop مشخص، بدون اعتماد کور به X-Forwarded-For. static hosting/GitHub Pages برای بک‌اند کافی نیست؛ GitHub فقط مخزن و release/CI، سرور Python برای اجرای ابزارها لازم است.

## 19. مراحل اجرایی و معیار پایان

### مرحله A — پایه و برند

factory، config فایل، ورود، csrf، health/capabilities، sidebar و صفحات دو زبان/دو تم، لوگوی همراه، fonts local و build آیکون‌ها. معیار: بدون DB بالا بیاید، admin/123456 در local کار کند، public ناامن شروع نشود، RTL سالم.

### مرحله B — دامنه و منابع

updater اتمیک، منابع bundled، validator IDN، RDAP routing، adapter واقعی ir، limiter، batch و export. معیار: خطای شبکه هیچ‌وقت آزاد نشود، ir و com مسیر درست داشته باشند، partial و cancel کار کنند.

### مرحله C — ابزارها و terminal

DNS، Ping adapterهای سه سیستم، IP/CIDR/PTR/RDAP، HTTP/TLS، SSE و snapshot. معیار: terminal داده واقعی، cancel subprocess را متوقف کند، .json.txt با JSON parser خوانده شود.

### مرحله D — سخت‌سازی و تحویل

تست سیاست مقصد، کنترل حافظه، مقیاس SSE، accessibility، mobile، release Docker و native، README دو زبان، license و notices، گزارش validation با محدودیت‌ها. هر قابلیت خارج از محیط آزمون صریحاً unverified اعلام شود. اجرای موفق mock را معادل آزمون واقعی Windows/macOS ندان.

## 20. آزمون‌های لازم

- fixture RDAP: registered، 404 معتبر، HTML 404، 429، 503، wrong object، wrong domain، redirect و timeout؛ WHOIS ir پاسخ واقعی sanitised و unknown message.
- normalization: IDN فارسی، uppercase، trailing dot، duplicate، BOM، co.uk، subdomain، label/length نامعتبر، Unicode control، TLD ناموجود؛ DNS SRV جدا.
- IP policy: loopback، RFC1918، IPv6 local، mapped IPv4، rebinding/redirect به private و host با چند A/AAAA متفاوت. public HTTP/TLS/Ping نتوانند metadata را بزنند.
- authentication: local defaults، public guard، login/logout، CSRF، expiry، session/job isolation، export بدون مجوز، credential redaction.
- job state: cancellation، capacity، TTL، last-event-id و resync، bounded output، shutdown، semaphore release در exception.
- updater: 304، malformed، قطع دانلود، concurrent update، rollback، atomic replace و حفظ منبع قبلی.
- JSON/TXT/JSON.TXT: فارسی UTF-8، schema پایدار، cancelled/partial، عدم secret و اعتبار parser.
- ping: argv هر OS، input injection، deadline/kill، binary absent، permission، locale unknown؛ native smoke روی OSهای در دسترس.
- frontend: keyboard، mobile 360px، fa/en، dark/light/system، loading/cancel، reduced motion، no untranslated strings، CSS و icon bundle فقط مورد نیاز.

CI Linux/Windows/macOS برای unit tests و build؛ live DNS/RDAP tests opt-in و کم‌تعداد، نه وابسته به آزاد بودن یک دامنه اتفاقی. network failure تست‌ها را به موفقیت تبدیل نکن. integration network با transport mock و fixture؛ smoke واقعی جدا گزارش شود.

بودجه اولیه UI: CSS gzip زیر 60KiB و JS gzip زیر 100KiB بدون فونت؛ هدف اجرایی است و اندازه واقعی در release ثبت شود. حداکثر دو خانواده فونت UI با subset و بارگیری به اندازه نیاز. benchmark با سخت‌افزار، تعداد هدف، منبع و نرخ خطا؛ سرویس بیرونی SLA خود برنامه نیست.

## 21. Definition of Done نهایی

- [ ] پنل قابل اجرا بدون DB و سرویس اجباری پولی.
- [ ] ورود پیشفرض محلی، تنظیم رمز امن برای public و نشست معتبر.
- [ ] فارسی/انگلیسی کامل، RTL/LTR، light/dark و فونت‌های محلی.
- [ ] batch domain از paste/TXT/generator با وضعیت‌های دقیق.
- [ ] RDAP و ir واقعی، پوشش/unsupported شفاف، updater دستی با حفظ آخرین نسخه سالم.
- [ ] DNS/Dig، Ping، IP/CIDR/PTR/IP-RDAP، HTTP و TLS واقعی.
- [ ] ترمینال زنده، cancel، partial و خروجی JSON/TXT/JSON.TXT معتبر.
- [ ] بدون ذخیره خودکار ورودی و نتیجه، memory/timeout/queue محدود.
- [ ] حفاظت مقصد public، shell=False، CSRF و redaction.
- [ ] Linux اصلی و راهنمای صادقانه Windows/macOS، capability detection.
- [ ] build سبک، آیکون‌های منتخب، no runtime CDN، بدون mock در محصول.
- [ ] README دو زبان، MIT برای کد اصلی و notices مجوز وابستگی‌ها/فونت‌ها/PSL.
- [ ] گزارش تست، محدودیت‌های شناخته‌شده و CHECKLIST تکمیل‌شده؛ هیچ کلید/رمز واقعی در git.

## 22. منابع رسمی و ملاحظات اعتبار

منابع زیر مبنای تصمیم فنی در زمان نوشتن سند هستند؛ Agent قبل pin وابستگی‌ها مستندات نسخه مورد استفاده را تطبیق دهد.

- Flask async/background-task limitations: https://flask.palletsprojects.com/en/stable/async-await/
- Flask deployment / Waitress: https://flask.palletsprojects.com/en/stable/deploying/waitress/
- Tailwind CLI: https://tailwindcss.com/docs/installation/tailwind-cli
- Lucide packages: https://lucide.dev/packages
- RDAP discovery RFC 9224: https://www.rfc-editor.org/rfc/rfc9224.html
- RDAP query RFC 9082: https://www.rfc-editor.org/rfc/rfc9082.html
- IANA DNS bootstrap: https://data.iana.org/rdap/dns.json
- IANA .ir: https://www.iana.org/domains/root/db/.ir.html
- Public Suffix List: https://publicsuffix.org/list/
- ICANN RDAP transition: https://www.icann.org/en/announcements/details/icann-update-launching-rdap-sunsetting-whois-27-01-2025-en

## 23. English handoff contract

Build NetNama, a lightweight bilingual Persian/English domain and network toolbox, using Flask, Jinja2, compiled Tailwind CSS and selected Lucide icons. This is a custom admin-style UI, not Django Admin. Do not add a database, Redis, Celery, SPA framework or mandatory paid API. Runtime results live in bounded process memory with a TTL; files store only configuration, credentials as hashes, and manually updated reference datasets. Exports are explicit downloads, never automatic server-side history.

Local bootstrap credentials must be admin / 123456 as requested. Bind localhost by default; public mode requires changing the default password and setting a strong secret. All tools run from the server, including ICMP Ping. Do not present server measurements as client measurements. Support Linux first, and implement/test platform-specific Windows/macOS adapters honestly.

Use authoritative IANA RDAP discovery plus explicitly supported WHOIS adapters, including .ir. A validated no-match means likely available, never guaranteed purchasable. Do not infer registration availability from DNS failure or HTTP errors. Include batch input, TXT import, name/TLD generation, DNS dig-style output, Ping, IP classification, CIDR, PTR, IP RDAP, HTTP headers and TLS inspection. Provide live bounded terminal events, cancellation and TXT/JSON/JSON.TXT export; the latter must contain valid JSON.

Use a process-lifetime bounded scheduler rather than spawning request-local asyncio tasks. Single-process deployment is intentional. Use session ownership, CSRF, explicit target validation, DNS rebinding-safe HTTP/TLS connections, restricted subprocess arguments and public-mode blocks on private/internal addresses. Protect response size, concurrency and memory. Manual updates must validate data and atomically replace only successful resources while retaining the previous valid version.

Follow all Persian sections above as normative acceptance criteria. Ship real working functionality, bilingual documentation, tests, a Linux Docker image, native instructions, local fonts, vector branding, dependency locks and an honest verification report. No fake success, placeholder metrics or unsupported tool buttons.
