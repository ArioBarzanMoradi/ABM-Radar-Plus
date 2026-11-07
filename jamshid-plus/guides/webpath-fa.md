# نصب مستقیم از GitHub و ورود با دامنه و Web Path

نسخهٔ 1.2 از مسیر دلخواه پشت Nginx پشتیبانی می‌کند؛ مانند:
`https://YOUR_DOMAIN:10443/YOUR_PATH/`

پورت 10443 برای هم‌زمانی با 3x-ui روی 443 انتخاب شده است.
Web Path جایگزین نام کاربری و گذرواژه نیست.

## نصب مستقیم روی Ubuntu

```bash
sudo apt update
sudo apt install -y git python3 curl iputils-ping traceroute
git clone https://github.com/ArioBarzanMoradi/Jamshid-Radar-Plus.git
cd Jamshid-Radar-Plus
sudo bash install.sh --port 8788
```

## پیش‌نیاز دامنه

- رکورد A دامنه به IPv4 واقعی همین سرور اشاره کند.
- اگر AAAA می‌سازی، IPv6 نیز باید به همین سرور برسد.
- Nginx نصب و در حال اجرا باشد و پورت انتخابی آزاد باشد.
- گواهی معتبر دامنه و کلید آن از قبل آماده باشد. ابزار زیر گواهی صادر نمی‌کند.
- برای دریافت گواهی تازه، شیوهٔ Certbot را با توجه به سرویس فعلی روی 80 انتخاب کن؛ هیچ سرویس موجودی را بدون بررسی متوقف نکن.
- برای 10443 در Cloudflare از DNS only استفاده کن؛ این پورت جزو پورت‌های معمول پراکسی Cloudflare نیست.

## تنظیم HTTPS و Web Path

از ریشهٔ مخزن اجرا کن؛ مقادیر YOUR_DOMAIN و YOUR_PATH را جایگزین کن:

```bash
sudo bash configure-web.sh \
  --domain YOUR_DOMAIN \
  --path /YOUR_PATH/ \
  --port 10443
```

مسیر گواهی پیش‌فرض:
`/etc/letsencrypt/live/YOUR_DOMAIN/fullchain.pem`
و مسیر کلید:
`/etc/letsencrypt/live/YOUR_DOMAIN/privkey.pem`

برای گواهی در مسیر دیگر، `--cert /absolute/fullchain.pem --key /absolute/privkey.pem` اضافه کن.
اسکریپت Nginx را بررسی می‌کند، فایل اختصاصی جمشید می‌سازد، مبدأ عمومی پنل را تنظیم می‌کند و سرویس‌ها را بازخوانی می‌کند. در خطا تنظیم قبلی را برمی‌گرداند. تنظیم VPN روی 443 را تغییر نمی‌دهد.

پورت TCP/10443 را در فایروال میزبان و ارائه‌دهنده باز کن. اگر UFW فعال است:

```bash
sudo ufw allow 10443/tcp
```

آدرس چاپ‌شده را در مرورگر باز کن. اسلش پایانی مسیر حفظ می‌شود.
برای عامل‌های راه‌دور نیز **تمام نشانی، شامل Web Path** را وارد کن.
عامل روی خود سرور مرکزی همچنان می‌تواند از `http://127.0.0.1:8788` استفاده کند.

اگر نشانی بدون شمارهٔ پورت، یعنی HTTPS روی 443 می‌خواهی، ابتدا باید معماری اشتراک پورت با Xray موجود بررسی شود؛ این نسخه هیچ سرویس روی 443 را جابه‌جا نمی‌کند.

مرجع: https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_pass
