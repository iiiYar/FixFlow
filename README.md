# FixFlow - نظام إدارة خدمات الصيانة

## 📌 نظرة عامة

FixFlow هو تطبيق ويب متكامل لإدارة خدمات الصيانة، مصمم لتبسيط عمليات تتبع العملاء وطلبات الصيانة.

## ✨ الميزات الرئيسية

### إدارة العملاء
- تسجيل وإدارة معلومات العملاء
- تتبع العملاء الجدد والنشطين
- سجل كامل لتفاصيل العملاء

### إدارة الصيانة
- تسجيل طلبات الصيانة
- تتبع حالات الصيانة (قيد الانتظار، جاري الصيانة، مكتملة)
- حساب معدل إنجاز الصيانات

### لوحة المعلومات
- إحصائيات شاملة عن:
  * إجمالي العملاء
  * الصيانات النشطة
  * صيانات اليوم
  * إجمالي الإيرادات

### المميزات التقنية
- واجهة مستخدم سهلة وسريعة
- تصميم متجاوب
- دعم وضع الليل والنهار
- نظام مصادقة آمن

## 🛠 التقنيات المستخدمة

### الخلفية (Backend)
- Python
- Flask
- SQLAlchemy
- MySQL

### الواجهة الأمامية (Frontend)
- HTML5
- CSS3
- JavaScript
- Bootstrap

### أدوات إضافية
- Docker
- Font Awesome
- Chart.js

## 📦 متطلبات التثبيت

### المتطلبات
- Python 3.8+
- MySQL
- pip
- docker (اختياري)

### خطوات التثبيت
1. استنساخ المستودع
   ```bash
   git clone https://github.com/your-username/FixFlow.git
   ```

2. إنشاء بيئة افتراضية
   ```bash
   python -m venv venv
   source venv/bin/activate  # على Linux/Mac
   venv\Scripts\activate     # على Windows
   ```

3. تثبيت التبعيات
   ```bash
   pip install -r requirements.txt
   ```

4. إعداد قاعدة البيانات
   ```bash
   flask db upgrade
   ```

5. تشغيل التطبيق
   ```bash
   flask run
   ```

## 🐳 تثبيت Docker

### المتطلبات المسبقة
- Docker Desktop
- Docker Compose

### خطوات التثبيت على Windows
1. تحميل Docker Desktop
   ```bash
   https://www.docker.com/products/docker-desktop
   ```

2. تثبيت Docker Desktop
   - تشغيل المثبت
   - اتباع خطوات المعالج
   - إعادة التشغيل عند الانتهاء

3. التحقق من التثبيت
   ```bash
   docker --version
   docker-compose --version
   ```

### تشغيل التطبيق باستخدام Docker
1. استنساخ المستودع
   ```bash
   git clone https://github.com/your-username/FixFlow.git
   cd FixFlow
   ```

2. بناء وتشغيل الحاويات
   ```bash
   docker-compose up --build -d
   ```

3. الوصول للتطبيق
   - الموقع الرئيسي: `http://localhost:80`
   - phpMyAdmin: `http://localhost:8080`

### أوامر Docker المهمة
- إيقاف الحاويات: `docker-compose down`
- عرض الحاويات: `docker-compose ps`
- عرض السجلات: `docker-compose logs`

### استكشاف الأخطاء
- التأكد من تشغيل Docker Desktop
- التحقق من إعدادات الشبكة
- مراجعة ملف docker-compose.yml

## 🔐 الدخول

- اسم المستخدم الافتراضي: `admin`
- كلمة المرور الافتراضية: `admin123`

## 🚀 المميزات القادمة
- دعم لغات متعددة
- تقارير متقدمة
- تكامل مع أنظمة الدفع

## 🤝 المساهمة
1. عمل Fork للمشروع
2. إنشاء branch جديد
3. تنفيذ التغييرات
4. عمل Pull Request

## 📄 الترخيص
مرخص تحت MIT License

## 📧 للتواصل
- البريد الإلكتروني: support@fixflow.com
- موقع الويب: www.fixflow.com
