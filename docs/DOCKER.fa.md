# راه‌اندازی نِت‌نما روی سرور با Docker

با Docker Engine و Docker Compose نسخهٔ **2.24 یا جدیدتر** در ریشهٔ پروژه فقط اجرا کنید:

```sh
docker compose up -d --build
```

نشانی: **http://SERVER_IP:8080**؛ روی رایانهٔ خودتان **http://localhost:8080**.
ورود اولیه **admin / 123456** است. رمز را می‌توانید از «منابع و تنظیمات» برنامه
تغییر دهید. برای شروع نیازی به ساخت `.env`، انتخاب رمز، تولید secret، دامنه یا
نصب Nginx نیست. برنامه با همان `.env.example` همراه پروژه بالا می‌آید.
اگر volume از قبل وجود دارد، رمز ذخیره‌شدهٔ قبلی معتبر است.

## ۱. تنظیمات اختیاری

Compose ابتدا `.env.example` را می‌خواند و اگر `.env` موجود باشد، مقدارهای آن را
جایگزین می‌کند. برای تغییر نام کاربری اولیه، رمز اولیه، HTTPS یا سقف نگه‌داری
نتایج، همان `.env.example` را ویرایش کنید یا یک `.env` خصوصی بسازید. کپی یا تغییر
هیچ فایلی برای اجرای پیشفرض لازم نیست. خود برنامهٔ پایتون هنگام اجرای خارج از
Docker فایل‌های env را خودکار نمی‌خواند.

- `NETNAMA_USERNAME=admin` و `NETNAMA_PASSWORD=123456`: ورود اولیه.
- `NETNAMA_SECRET_KEY=`: مقدار خالی یعنی ساخت خودکار secret تصادفی و ذخیره روی volume.
- `NETNAMA_HTTPS=false`: اجرای HTTP بدون تنظیمات اضافه؛ در صورت استفاده از HTTPS آن را `true` کنید.
- `NETNAMA_RESULT_TTL=900`: نگه‌داری نتایج، بین 30 و 3600 ثانیه.
- `NETNAMA_MAX_RAM_MB=48`: سقف پذیرش دادهٔ کارهای ذخیره‌شده، بین 8 و 256 مگابایت.

رمز محیطی تنها در اولین اجرای volume خالی اعمال می‌شود. رمز موجود را از پنل
برنامه عوض کنید؛ ویرایش فایل env آن را بازنویسی نمی‌کند. secret خودکار بین
restartها ثابت می‌ماند و نیازی به تنظیم دستی ندارد.

پیشفرض پورت 8080 روی همهٔ رابط‌های میزبان منتشر می‌شود. اگر پورت دیگری خواستید:

```sh
NETNAMA_HTTP_PORT=9090 docker compose up -d --build
```

برای محدود کردن پورت به خود میزبان، مثلاً پشت Nginx:

```sh
NETNAMA_BIND_ADDRESS=127.0.0.1 docker compose up -d
```

`NETNAMA_HTTP_PORT`، `NETNAMA_BIND_ADDRESS` و `NETNAMA_MEMORY_LIMIT` تنظیمات خود
Compose هستند و باید در شل یا `.env` اختیاری قرار گیرند. سقف RAM کانتینر پیشفرض
512m است. پورت داخل کانتینر همیشه 8080 و حالت اجرا عمومی است؛ دسترسی ابزارها به
مقصدهای خصوصی شبکه مسدود می‌ماند.

## ۲. وضعیت و ساخت

```sh
docker compose ps
curl --fail http://127.0.0.1:8080/healthz
```

اگر می‌خواهید دستور تا سالم شدن سرویس منتظر بماند:

```sh
docker compose up -d --build --wait --wait-timeout 120
```

فرانت‌اند داخل build با lockfile ساخته می‌شود؛ Node در ایمیج نهایی نیست. اولین
build به Docker Hub، registry.npmjs.org، pypi.org و files.pythonhosted.org نیاز
دارد. اجرای دفعات بعد با ایمیج موجود نیازی به دریافت وابستگی‌ها ندارد:
`docker compose up -d`. داده‌های مرجع همراه ایمیج هستند.

برنامه تک‌پردازه است؛ برای این نسخه از scale یا چند worker استفاده نکنید.

## ۳. دامنه و HTTPS (اختیاری)

رکورد A دامنه را روی IP سرور بگذارید. AAAA را تنها زمانی تنظیم کنید که مسیر IPv6
سرور و پراکسی هم آماده باشد. پورت‌های عمومی 80 و 443 برای پراکسی لازم هستند.

فایل [`deploy/nginx.conf.example`](../deploy/nginx.conf.example) نمونهٔ Nginx
**نصب‌شده روی میزبان** است. دامنه، مسیر گواهی معتبر TLS و پورت upstream را تنظیم
کنید، سپس با `sudo nginx -t` بررسی و Nginx را reload کنید. نمونه عمداً گواهی صادر
نمی‌کند؛ گواهی و تمدید خودکار آن را با روش معمول سرور مثل Certbot فراهم کنید.

پراکسی باید Host اصلی را حفظ کند. buffering و cache برای رویدادهای زنده خاموش و
read timeout بیشتر از 75 ثانیه باشد؛ نمونه این موارد را تنظیم کرده است. برنامه
به forwarded headerها اعتماد نمی‌کند و برای اجرای معمول نیازی به ProxyFix ندارد.

اگر پراکسی خودش کانتینری است، `127.0.0.1:8080` داخل آن به نِت‌نما اشاره نمی‌کند.
دو سرویس را در شبکهٔ Docker مشترک قرار دهید و upstream را `netnama:8080` بگذارید؛
در این حالت می‌توانید انتشار پورت سرویس نِت‌نما روی میزبان را حذف کنید.

پس از استقرار، ورود، ساخت نام، یک بررسی دامنه، پیشرفت زنده و دانلود نتیجه را
از دامنهٔ HTTPS آزمایش کنید.

## ۴. داده، به‌روزرسانی و پشتیبان

volume نام‌دار `netnama-data` زیر مسیر `/data` تنظیمات، hash رمز و منابع به‌روز‌شده
را نگه می‌دارد. نام واقعی volume شامل پیشوند پروژهٔ Compose است؛ نام پروژه و مسیر
استقرار را بین اجراها ثابت نگه دارید. نام را با `docker volume ls --filter label=com.docker.compose.volume=netnama-data` ببینید.
کاربر کانتینر UID/GID برابر 10001 دارد. named volume تازه، مجوز درست را از ایمیج
می‌گیرد. اگر به‌جای آن bind mount می‌گذارید، مالک پوشه را به `10001:10001` بدهید.

برای به‌روزرسانی پس از دریافت کد جدید:

```sh
docker compose up -d --build --wait --wait-timeout 120
docker compose ps
```

بازسازی و restart، تنظیمات روی volume را نگه می‌دارد؛ **نشست‌ها و کارهای در RAM
از بین می‌روند**. پیش از ارتقا، پایان کارهای فعال را منتظر بمانید. برای توقف:

```sh
docker compose down
```

`docker compose down -v` تنظیمات و منابع ذخیره‌شده را هم حذف می‌کند؛ برای ارتقا یا
توقف معمول از آن استفاده نکنید. برای backup سازگار، ابتدا سرویس را متوقف کنید:

```sh
umask 077
docker compose stop
docker compose run --rm --no-deps -T --entrypoint python netnama -c 'import sys, tarfile; t=tarfile.open(fileobj=sys.stdout.buffer, mode="w|"); t.add("/data", arcname="data"); t.close()' > netnama-data.tar
docker compose up -d --wait
```

این فایل شامل hash رمز و secret است؛ در محل خصوصی نگه دارید و `.env` را جداگانه
پشتیبان بگیرید، اگر آن را ساخته‌اید. بازگردانی را فقط روی volume خالیِ استقرار بازیابی و از backup
مطمئن خودتان انجام دهید:

```sh
docker compose stop
docker compose run --rm --no-deps -T --entrypoint python netnama -c 'import sys, tarfile; t=tarfile.open(fileobj=sys.stdin.buffer, mode="r|*"); t.extractall(path="/", filter="data")' < netnama-data.tar
docker compose up -d --wait
```

## ۵. عیب‌یابی و محدودیت‌های شبکه

```sh
docker compose ps
docker compose logs --tail=100 netnama
docker compose exec -T netnama python -c 'import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:8080/healthz", timeout=3).status)'
```

- خطای resolve هنگام build: DNS و دسترسی خروجی **Docker daemon/build** را بررسی
  کنید. کارکرد اینترنت میزبان الزاماً به معنی کارکرد اینترنت داخل Docker نیست.
  وابستگی‌ها یا بررسی TLS/hash را برای حل این مشکل غیرفعال نکنید.
- اگر سرور به registryها دسترسی ندارد، ایمیج را روی ماشین دارای دسترسی با معماری
  یکسان بسازید، با `docker save` منتقل و با `docker load` بارگذاری کنید. برای
  مثال ایمیج را `netnama:release` تگ بزنید و یک override با
  `services: {netnama: {image: 'netnama:release'}}` بسازید؛ سپس
  `docker compose -f compose.yaml -f compose.image.yaml up -d --no-build --wait`
  را اجرا کنید. فایل override را `compose.image.yaml` بنامید.
- خطای permission روی `/data`: مالک bind mount یا volume بازیابی‌شده را بررسی کنید.
- خطای ورود: برای volume قدیمی همان رمز ذخیره‌شده معتبر است؛ برای HTTPS کوکی
  Secure باید فعال باشد و آدرس مرورگر هم HTTPS باشد.
- بررسی دامنه به DNS و HTTPS خروجی و برای `.ir` به TCP خروجی پورت 43 نیاز دارد.
  بعضی ارائه‌دهندگان پورت 43 را مسدود می‌کنند. DNS سفارشی به UDP/TCP پورت 53
  خروجی نیاز دارد. محدودیت رجیستری یا شبکه نتیجهٔ «آزاد» تولید نمی‌کند.
- ایمیج حداقلی عمداً binary پینگ ندارد؛ قابلیت Ping در آن unavailable است.
  سایر ابزارها از داخل شبکهٔ کانتینر اجرا می‌شوند. برای این استقرار privileged
  یا capability اضافی لازم نیست.
- Docker پس از unhealthy شدن، خودبه‌خود کانتینر زنده را restart نمی‌کند؛
  `restart: unless-stopped` فقط خروج پردازه را پوشش می‌دهد. وضعیت سلامت را با
  ابزار مانیتورینگ سرور پیگیری کنید. لاگ‌ها با سقف 3 فایل 10 مگابایتی محدودند.

## آزمون قابل تکرار

```sh
python3 scripts/docker_smoke.py --defaults
```

این دستور ایمیج را می‌سازد و پروژه و volume **آزمایشیِ جداگانه** ایجاد می‌کند؛
سلامت، ورود، فایل‌های رابط، نام‌سازی، کار محلی، خروجی، نگه‌داری تنظیمات پس از
restart، کوکی Secure، پشتیبان‌گیری/بازیابی و اجرای non-root/read-only را بررسی می‌کند. در پایان فقط منابع همان
آزمایش را پاک می‌کند. تست رجیستری خارجی انجام نمی‌دهد. برای ایمیجی که قبلاً
ساخته‌اید: `python3 scripts/docker_smoke.py --defaults --image netnama:release --skip-build`.
