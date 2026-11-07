# جمشید پلاس · Jamshid Plus 1.2

پنل فارسی پایش واقعی سرورهای لینوکسی، با رابط شیشه‌ای جمشید و پشتیبانی دامنه و Web Path.

## نصب مستقیم روی Ubuntu

```bash
sudo apt update
sudo apt install -y git python3 curl iputils-ping traceroute
git clone https://github.com/ArioBarzanMoradi/Jamshid-Radar-Plus.git
cd Jamshid-Radar-Plus
sudo bash install.sh --port 8788
```

نصب‌کننده نام کاربری و گذرواژهٔ مدیر را می‌پرسد.

برای دامنه و مسیر دلخواه، پس از آماده‌کردن Nginx و گواهی معتبر دامنه:

```bash
sudo bash configure-web.sh --domain YOUR_DOMAIN --path /YOUR_PATH/ --port 10443
```

نشانی پنل: `https://YOUR_DOMAIN:10443/YOUR_PATH/`
پورت 443 برای VPN فعلی حفظ می‌شود.

- [راهنمای کامل دامنه، SSL و Web Path](jamshid-plus/guides/webpath-fa.md)
- [README کامل پروژه و اتصال عامل‌ها](jamshid-plus/README.md)
- [گزارش بررسی‌ها](jamshid-plus/VERIFICATION.md)

سورس جاری در پوشهٔ **jamshid-plus** قرار دارد. پوشهٔ radar-infra نسخهٔ قدیمی است؛ نصب‌کنندهٔ ریشه، نسخهٔ جاری را انتخاب می‌کند.
