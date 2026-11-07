# انتشار جمشید پلاس در GitHub

<div dir="rtl">

نام پیشنهادی: **jamshid-plus**  
توضیح کوتاهٔ مخزن: **Self-hosted Persian Linux monitoring · Jamshid glass UI · real per-host agents**

## بارگذاری از مک با Git

در GitHub یک مخزن خالی با نام دلخواه بساز. گزینهٔ افزودن README اولیه را انتخاب نکن، چون README داخل این بسته آماده است. ZIP را استخراج کن. در ترمینال وارد **پوشهٔ jamshid-plus که README.md داخل آن است** شو.

نشانی زیر را با URL مخزن خودت عوض کن:

</div>

```bash
git init -b main
git add .
git commit -m "Prepare Jamshid Plus v1.1.0"
git remote add origin https://github.com/YOUR_USERNAME/jamshid-plus.git
git push -u origin main
```

<div dir="rtl">

از حساب GitHub، کلید SSH، GitHub Desktop یا credential manager خودت برای ورود استفاده کن. فایل‌های واقعی پیکربندی، داده و کلید عامل خارج از مخزن می‌مانند. بستهٔ تحویلی هیچ گذرواژه یا کلید عامل از پیش تعیین‌شده ندارد.

اگر قصد به‌روزرسانی مخزن موجود را داری، اول آن را clone کن و تغییرات این نسخه را روی همان checkout اعمال کن؛ تاریخچهٔ مخزن را با دستورهای بالا بازنویسی نکن.

## بارگذاری با رابط GitHub

از **Add file → Upload files**، محتوای داخل پوشهٔ jamshid-plus را بارگذاری کن. در ریشه باید README.md، install.sh، frontend/، radar/ و docs/ دیده شوند. برای فرستادن فایل‌های مخفی مثل .github و .gitignore، استفاده از Git یا GitHub Desktop کامل‌تر است.

## فعال‌سازی GitHub Pages

1. در مخزن، **Settings → Pages** را باز کن.
2. Source را **Deploy from a branch** بگذار.
3. شاخهٔ **main** و پوشهٔ **/docs** را انتخاب کن و Save بزن.
4. پس از موفقیت انتشار، **Visit site** صفحهٔ معرفی جمشید پلاس را باز می‌کند.

صفحه با نام کاربری و نام مخزن خودت سازگار است و لینک مخزن را روی دامنهٔ github.io تشخیص می‌دهد. برای دامنهٔ اختصاصی، نشانی لینک مخزن را در docs/assets/project.js وارد کن.

[انتخاب منبع Pages در راهنمای رسمی GitHub](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)

## اولین Release

1. بعد از push، تب Actions را بررسی کن. گردش **Validate Jamshid Plus** باید موفق شود.
2. ZIP نصب در artifact گردش CI با نام jamshid-plus-release ساخته می‌شود. فایل ZIP داخلی را دریافت کن.
3. از **Releases → Draft a new release** یک تگ **v1.1.0** روی main بساز.
4. عنوان را **جمشید پلاس 1.1.0** بگذار، تغییرات CHANGELOG.md را درج کن و ZIP را پیوست کن.
5. بعد از بازبینی خودت، Release را منتشر کن.

برای ساخت ZIP روی دستگاه خودت هم، پس از npm run build اجرا کن:

</div>

```bash
python3 scripts/package.py
```

<div dir="rtl">

فایل در dist/jamshid-plus-github-ready-v1.1.0.zip ساخته می‌شود. Node.js فقط برای توسعه یا بازسازی رابط است؛ نصب از ZIP آماده روی سرور به آن نیاز ندارد.

## پیشنهاد برای About مخزن

Topics:
linux, monitoring, self-hosted, network, observability, persian, rtl, wireguard, vpn, systemd

Website:
پس از فعال‌شدن Pages، نشانی واقعی Visit site را در بخش About مخزن بگذار.

تصویر داشبورد در docs/assets/dashboard-dark.png و تصویر روشن در docs/assets/dashboard-light.png آماده‌اند. README تصویر پوستهٔ زغالی را نشان می‌دهد.

</div>
