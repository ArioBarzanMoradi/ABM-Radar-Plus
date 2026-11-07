# اتصال چند سرور و نگهداری رادار

<div dir="rtl">

## آدرس درست پنل برای عامل

| محل عامل | نشانی ورودی نصب‌کننده |
|---|---|
| روی سرور مرکزی | `http://127.0.0.1:8787` با پورت واقعی پنل |
| روی سرور دیگری که تونل SSH زیر را اجرا می‌کند | `http://127.0.0.1:18787` |
| روی سرور دیگری که به دامنهٔ امن پنل می‌رسد | مانند `https://radar.example.net:9443` |

**روش SSH برای اولین اتصال.** از سرور عامل، یک نشست SSH جداگانه به سرور مرکزی باز کن. حساب SSH باید اجازهٔ port forwarding داشته باشد.

</div>

```bash
ssh -NT -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
  -L 127.0.0.1:18787:127.0.0.1:8787 USER@PANEL_IP
```

<div dir="rtl">

این نشست را باز نگه دار. در یک ترمینال دیگر **روی همان سرور عامل**، ابتدا `curl http://127.0.0.1:18787/healthz` را امتحان کن. باید `{"status":"ok"}` ببینی. سپس `sudo bash install-agent.sh` را اجرا کن و نشانی محلی پورت ۱۸۷۸۷ و کلید **همان میزبان** را وارد کن. قطع‌شدن نشست SSH مسیر عامل را قطع می‌کند. برای استفادهٔ دائمی، تونل مدیریت‌شدهٔ خودت یا HTTPS دائمی را به کار بگیر.

**روش دامنه و HTTPS.** اگر روی سرور مرکزی پراکسی معکوس و گواهی معتبر داری، یک نام و پورت آزاد مثل `radar.example.net:9443` برای رادار در نظر بگیر. در `/etc/radar-infra/panel.env`، خط `RADAR_PUBLIC_ORIGIN=https://radar.example.net:9443` را تنظیم کن و `sudo radarctl restart` را بزن. نشانی باید دقیقاً شامل نام و پورت بیرونی و بدون مسیر باشد. پورت داخلی همچنان ۸۷۸۷ است. نمونه برای **Nginx موجود** با گواهی همان دامنه و پورتی که از شبکهٔ عامل‌ها دسترسی دارد.

</div>

```nginx
server {
    listen 9443 ssl;
    server_name radar.example.net;
    ssl_certificate     /etc/letsencrypt/live/radar.example.net/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/radar.example.net/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8787;
        proxy_set_header Host $http_host;
    }
}
```

<div dir="rtl">

نمونه را با گواهی و دامنهٔ واقعی تنظیم کن. بعد از `sudo nginx -t` موفق، `sudo systemctl reload nginx` را اجرا کن. روی میزبان دارای 3x-ui روی ۴۴۳، این نمونه از TCP/9443 استفاده می‌کند. گواهی TLS، رکورد DNS و دسترسی شبکه به پورت انتخابی را متناسب با سرور خودت فراهم کن. عامل گواهی را از طریق CAهای مورد اعتماد سیستم بررسی می‌کند و تغییر مسیر HTTP را نمی‌پذیرد.

## تشخیص 3x-ui، WireGuard، Outline و تونل‌ها

نام سرویس را در **ویرایش سرور ← سرویس‌ها و تونل‌ها** ثبت کن. سپس روی همان عامل، نگاشت دلخواه را در بخش `checks` فایل `/etc/radar-agent/config.json` قرار بده. **مقدار کلید اختصاصی موجود در فایل را حفظ کن.** مثال زیر فقط مقدار بخش `checks` است. فایل آمادهٔ همین مثال در [agent/checks.example.json](../agent/checks.example.json) است.

</div>

```json
{
  "3x-ui": {"unit": "x-ui.service"},
  "WireGuard": {"interface": "wg0"},
  "Outline": {"listen": {"protocol": "TCP", "port": 23456}},
  "تونل آلمان": {"unit": "rathole.service"}
}
```

<div dir="rtl">

- **واحد systemd** از وضعیت واحد همان میزبان استفاده می‌کند. نام واحد را متناسب با نصب خودت انتخاب کن.
- **رابط شبکه** پرچم UP رابط را می‌خواند. برای WireGuard، این شاخص وضعیت رابط را نشان می‌دهد. برای ارزیابی عبور ترافیک، از تست مقصد درون تونل هم استفاده کن.
- **شنود پورت** برای سرویس کانتینری‌ای مفید است که سوکت آن در فضای شبکهٔ میزبان دیده می‌شود. برای Outline، عدد نمونهٔ ۲۳۴۵۶ را با پورت واقعی عوض کن. در برخی تنظیمات Docker انتشار پورت فقط با NAT انجام می‌شود. در این حالت، شاهد دیگری مثل واحد systemd معتبر انتخاب کن یا وضعیت را نامشخص بگذار. عامل به سوکت مدیریت Docker یا کلیدهای VPN نیاز ندارد.
- برای «تونل» می‌توانی در فرم یک سرور مقصد هم انتخاب کنی تا مسیر در نقشه دیده شود. این ارتباط در نقشه نشان‌دهندهٔ پیکربندی ثبت‌شده است.

بعد از تغییر، `sudo systemctl restart radar-agent` را اجرا کن. برای استفاده از کلید تازه، از پوشهٔ پروژه `sudo bash install-agent.sh --configure` را اجرا کن.

## عیب‌یابی

| نشانه | بررسی بعدی |
|---|---|
| پنل روی مک باز نمی‌شود | روی سرور `sudo radarctl status` و `curl http://127.0.0.1:8787/healthz` را بررسی کن. بعد پورت‌های مبدأ و مقصد در فرمان SSH را مقایسه کن. |
| عامل در انتظار اولین نمونه است | `sudo systemctl status radar-agent` و `sudo journalctl -u radar-agent -n 40 --no-pager` را روی همان میزبان ببین. پاسخ ۴۰۱ یعنی کلید با میزبان سازگار نیست. |
| خطای میزبان یا مبدأ درخواست | نشانی HTTPS بیرونی و `RADAR_PUBLIC_ORIGIN` باید یکسان باشند. پراکسی باید هدر Host شامل پورت بیرونی را منتقل کند. |
| CPU/RAM می‌آید ولی پینگ خالی است | مقصد `ping_target`، نصب `iputils-ping`، اجازهٔ ICMP برای کاربر عامل و پاسخ‌گویی مقصد را بررسی کن. |
| تست UDP نامشخص است | دریافت پاسخ می‌تواند UDP را تأیید کند. سکوت سرویس، از جمله WireGuard، برای نتیجهٔ باز یا بسته کافی نیست. از وضعیت رابط و یک تست داخل تونل کمک بگیر. |
| پورت در پنل دیده می‌شود ولی از اینترنت وصل نمی‌شود | شاخص پورت محلی از سوکت میزبان می‌آید. برای آزمایش مسیر، تست را از عامل دیگری به IP یا دامنه و پورت مقصد اجرا کن. |
| فرم تست می‌گوید مقصد ثبت نشده | IP یا دامنه را در مشخصات یکی از سرورهای ثبت‌شده اضافه کن. عامل فقط پنج نوع تست مشخص را اجرا می‌کند. |

پایش مصرف منابع و آخرین نمونه حتی با مرورگر بسته ادامه دارد. بازهٔ «بازخوانی داشبورد» تنها فاصلهٔ تازه‌کردن داده‌های رابط است. رادار یک نمونه در هر دقیقه برای هر میزبان را تا هفت روز نگه می‌دارد و نمودار را از همان داده‌ها می‌سازد. هر تست دو دقیقه فرصت دارد تا نتیجهٔ قابل ثبت بدهد. صفحهٔ جزئیات حداکثر ۱۰۰ نتیجهٔ آخر و صفحهٔ رخدادها تا ۲۰۰۰ رخداد آخر را نمایش می‌دهد. SQLite تاریخچهٔ ثبت‌شده را نگه می‌دارد.

## انتشار سورس با Git از مک

برای یک مخزن خالی روی GitHub، از داخل **پوشه‌ای که README.md در آن قرار دارد** اجرا کن. در نشانی نمونه، نام حساب و مخزن خودت را جایگزین کن.

</div>

```bash
git init -b main
git add .
git commit -m "Add self-hosted Radar infrastructure dashboard"
git remote add origin https://github.com/YOUR_USERNAME/radar-infra.git
git push -u origin main
```

<div dir="rtl">

اگر حساب GitHub به احراز هویت نیاز دارد، از GitHub Desktop، Git Credential Manager یا کلید SSH خودت استفاده کن. کلید عامل، نسخهٔ پشتیبان و فایل پیکربندی واقعی را به مخزن اضافه نکن. برای ارائهٔ دانلود تک‌فایلی می‌توانی همین ZIP را بعداً به یک GitHub Release هم پیوست کنی.

## ارتقا و نسخهٔ پشتیبان

قبل از ارتقا `sudo radarctl backup` را اجرا کن و مسیر چاپ‌شده را نگه دار. بعد `git pull --ff-only` و `sudo bash install.sh` را در پوشهٔ مخزن اجرا کن. فایل پیکربندی در `/etc/radar-infra/panel.env` و داده‌ها در `/var/lib/radar-infra` هستند. مسیر اجرای نسخهٔ جاری `/opt/radar-infra/current` است. برای عامل، اجرای مجدد `sudo bash install-agent.sh` کد را به‌روز می‌کند و تنظیمات اتصال موجود را حفظ می‌کند.

**بازیابی.** نسخهٔ پشتیبان را مانند دادهٔ خصوصی نگه دار. پیش از بازیابی یک پشتیبان تازه از وضعیت فعلی بگیر، سپس سرویس را متوقف کن. فرمان‌های زیر را در یک پوستهٔ root و پس از جایگزینی مسیر `BACKUP` اجرا کن. فایل‌های حالت قبلی برای بازگشت کنار گذاشته می‌شوند.

</div>

```bash
sudo -i
BACKUP=/absolute/path/to/backup.sqlite3
test -f "$BACKUP" || exit 1
systemctl stop radar-infra
STATE=/var/lib/radar-infra
PREVIOUS=$(mktemp -d /var/lib/radar-infra/previous.XXXXXXXX)
for part in radar.sqlite3 radar.sqlite3-wal radar.sqlite3-shm; do
  if [ -f "$STATE/$part" ]; then mv "$STATE/$part" "$PREVIOUS/"; fi
done
install -o radar-panel -g radar-panel -m 0600 "$BACKUP" "$STATE/radar.sqlite3"
radarctl set-admin
systemctl start radar-infra
radarctl status
exit
```

<div dir="rtl">

</div>
