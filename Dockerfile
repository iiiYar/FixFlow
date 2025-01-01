# استخدام Python 3.9 slim
FROM python:3.9-slim-bullseye

# تحديث وتثبيت التبعيات
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    default-libmysqlclient-dev \
    build-essential \
    pkg-config \
    libmariadb-dev \
    && rm -rf /var/lib/apt/lists/*

# إنشاء مستخدم للتطبيق
RUN addgroup --system appuser && \
    adduser --system --ingroup appuser appuser

# تعيين المجلد العامل
WORKDIR /app

# منح الصلاحيات للمستخدم
RUN mkdir -p /app/database && \
    chown -R appuser:appuser /app

# نسخ ملفات التبعيات
COPY --chown=appuser:appuser requirements.txt .

# تثبيت التبعيات
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir mysqlclient

# نسخ باقي الملفات
COPY --chown=appuser:appuser . .

# تبديل المستخدم
USER appuser

# منفذ التطبيق
EXPOSE 80

# الأمر التنفيذي
CMD ["flask", "run", "--host=0.0.0.0", "--port=80"]
