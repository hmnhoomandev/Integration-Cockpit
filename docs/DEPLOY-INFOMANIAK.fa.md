# انتشار روی Infomaniak، قدم‌به‌قدم

این راهنما نسخهٔ عمومی دمو را روی یک سرور Infomaniak در سوئیس با دامنهٔ خودتان و HTTPS بالا می‌آورد. نسخهٔ عمومی فقط دادهٔ ساختگی نشان می‌دهد و بارگذاری فایل واقعی در آن بسته است. **هرگز دادهٔ واقعی ASD را روی این سرور نگذارید.**

## ۱. خرید (در سایت Infomaniak)

1. یک **VPS Lite** بخرید.
   - ارزان‌ترین مدل (۱ پردازنده، ۲ گیگ RAM) کافی است.
   - سیستم‌عامل را **Ubuntu 24.04** انتخاب کنید.
   - موقع ساخت، Infomaniak یک کلید SSH از شما می‌خواهد یا یک کلید برایتان می‌سازد. آن کلید را نگه دارید.
2. یک **دامنه** بخرید، مثلاً `integrations-cockpit.ch`.
3. در صفحهٔ مدیریت VPS آدرس **IP** سرور را پیدا کنید (مثلاً `83.228.x.x`).

## ۲. تنظیمات در پنل Infomaniak

1. **فایروال VPS:** پورت‌های ورودی **22** (SSH)، **80** و **443** را باز کنید.
2. **DNS دامنه:**
   - یک رکورد **A** بسازید. نام آن `@` (یا خالی) باشد و مقدارش IP سرور.
   - اگر می‌خواهید `www` هم کار کند، یک رکورد A دیگر با نام `www` و همان IP بسازید.
   - تأثیر DNS ممکن است چند دقیقه تا چند ساعت طول بکشد.

## ۳. روی سرور (یک‌بار)

از ترمینال مک به سرور وصل شوید. مسیر کلید و IP را با مقدار خودتان عوض کنید:

```sh
ssh -i ~/Downloads/infomaniak-key ubuntu@IP-سرور
```

بعد روی سرور این دستورها را یکی‌یکی بزنید:

```sh
# Docker نصب می‌شود
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER && newgrp docker

# کد برنامه دانلود می‌شود
git clone https://github.com/hmnhoomandev/Integration-Cockpit.git
cd Integration-Cockpit/deploy

# دامنه را بنویسید (با دامنهٔ خودتان عوض کنید)
echo "DOMAIN=integrations-cockpit.ch" > .env

# حساب کاربری داورها ساخته می‌شود؛ رمز را می‌پرسد (حداقل ۱۲ حرف)
docker compose run --rm cockpit account bern-jury judge

# برنامه و HTTPS روشن می‌شوند
docker compose up -d --build
```

یک دقیقه صبر کنید و `https://integrations-cockpit.ch` را باز کنید. قفل HTTPS خودکار از Let's Encrypt گرفته می‌شود.

## ۴. بررسی

از کامپیوتر خودتان، در پوشهٔ پروژه، این را بزنید. رمز را می‌پرسد و نشانش نمی‌دهد:

```sh
python3 -m cockpit.smoke https://integrations-cockpit.ch bern-jury
```

اگر نوشت `Verified health, sign-in, …`، همه‌چیز درست است.

## کارهای بعدی

| کار | دستور (روی سرور، در پوشهٔ `Integration-Cockpit/deploy`) |
| --- | --- |
| نصب نسخهٔ جدید بعد از push | `git pull && docker compose up -d --build` |
| دیدن خطاها | `docker compose logs --tail 50` |
| عوض کردن رمز | `docker compose run --rm cockpit account bern-jury judge` |
| پشتیبان‌گیری | `docker compose exec cockpit python -m cockpit.server backup /data/backup.sqlite` |
| خاموش کردن | `docker compose down` (داده‌ها می‌مانند) |

**نکته‌ها**
- نام کاربری و رمز را فقط از کانال خصوصی برگزارکننده بفرستید، نه در GitHub یا اسکرین‌شات.
- دیتابیس در یک volume داکر به نام `cockpit-data` می‌ماند و با راه‌اندازی دوبارهٔ سرور پاک نمی‌شود.
- برنامه مستقیم از اینترنت در دسترس نیست. فقط Caddy (روی پورت‌های 80 و 443) به آن وصل می‌شود.
