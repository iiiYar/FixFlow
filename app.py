from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timedelta
import os
from sqlalchemy import func
from collections import defaultdict
import json
from werkzeug.utils import secure_filename
import requests
from functools import wraps
from flask import session, redirect, url_for
from flask_migrate import Migrate

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://fixflowuser:fixflowpassword@db/fixflowdb'
app.secret_key = 'your-secret-key-here'  # يجب تغيير هذا في الإنتاج
db = SQLAlchemy(app)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
migrate = Migrate(app, db)

# بيانات المستخدمين
USERS = {
    'admin': {
        'password': 'admin123',
        'role': 'admin'
    }
}

# Models
class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    workplace = db.Column(db.String(100), nullable=True)  # حقل جهة العمل اختياري
    repairs = db.relationship('Repair', backref='customer', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'workplace': self.workplace
        }

class Repair(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    device_type = db.Column(db.String(100), nullable=False)
    problem = db.Column(db.Text, nullable=False)
    cost = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default='قيد الانتظار')  # الحالات: قيد الانتظار، جاري الصيانة، تم الإصلاح، تم التسليم
    date = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'device_type': self.device_type,
            'problem': self.problem,
            'cost': self.cost,
            'status': self.status,
            'date': self.date
        }

class NotificationLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), nullable=False)  # نوع الإشعار (عميل جديد، تحديث حالة، الخ)
    status = db.Column(db.String(50), nullable=False)  # نجاح أو فشل
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'type': self.type,
            'status': self.status,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        }

# إنشاء قاعدة البيانات وجميع الجداول
def init_db():
    try:
        with app.app_context():
            # إنشاء جميع الجداول بغض النظر عن وجودها
            db.create_all()
            
            # التأكد من وجود بيانات أساسية
            if not Customer.query.first():
                # إضافة عميل تجريبي
                default_customer = Customer(
                    name='عميل تجريبي',
                    phone='0501234567',
                    workplace='مركز الصيانة'
                )
                db.session.add(default_customer)
                db.session.commit()
            
            if not Repair.query.first():
                # إضافة إصلاح تجريبي
                default_repair = Repair(
                    customer_id=1,
                    device_type='جهاز تجريبي',
                    problem='مشكلة تجريبية',
                    cost=100,
                    status='قيد الانتظار',
                    date=datetime.now()
                )
                db.session.add(default_repair)
                db.session.commit()
            
            # طباعة الجداول الموجودة
            print("الجداول في قاعدة البيانات:")
            for table in db.engine.table_names():
                print(table)
    
    except Exception as e:
        print(f"خطأ في إنشاء قاعدة البيانات: {e}")
        # إعادة رفع الخطأ للتأكد من توقف التطبيق
        raise

# Initialize database on startup
init_db()

# دالة لطباعة معلومات جدول العملاء
def print_customer_table_info():
    try:
        # طباعة أسماء الأعمدة
        columns = Customer.__table__.columns
        print("Customer Table Columns:")
        for column in columns:
            print(f"{column.name}: {column.type}")
        
        # عدد السجلات
        total_customers = Customer.query.count()
        print(f"Total Customers: {total_customers}")
        
        # عينة من البيانات
        sample_customers = Customer.query.limit(5).all()
        print("Sample Customers:")
        for customer in sample_customers:
            print(customer.__dict__)
    except Exception as e:
        print(f"Error examining Customer table: {str(e)}")

# دالة لطباعة معلومات جدول الصيانة
def print_repair_table_info():
    try:
        # طباعة أسماء الأعمدة
        columns = Repair.__table__.columns
        print("Repair Table Columns:")
        for column in columns:
            print(f"{column.name}: {column.type}")
        
        # عدد السجلات
        total_repairs = Repair.query.count()
        print(f"Total Repairs: {total_repairs}")
        
        # عينة من البيانات
        sample_repairs = Repair.query.limit(5).all()
        print("Sample Repairs:")
        for repair in sample_repairs:
            print(repair.__dict__)
    except Exception as e:
        print(f"Error examining Repair table: {str(e)}")

# دالة لطباعة معلومات الإيرادات
def print_revenue_details():
    try:
        today = datetime.now().date()
        first_day_of_month = today.replace(day=1)
        
        # إجمالي الإيرادات
        total_revenue = db.session.query(func.sum(Repair.cost)).scalar() or 0
        
        # إيرادات اليوم
        today_revenue = db.session.query(func.sum(Repair.cost)).filter(
            func.date(Repair.date) == today,
            Repair.status == 'تم الإصلاح'
        ).scalar() or 0
        
        # إيرادات الشهر
        month_revenue = db.session.query(func.sum(Repair.cost)).filter(
            func.date(Repair.date) >= first_day_of_month,
            Repair.status == 'تم الإصلاح'
        ).scalar() or 0
        
        # متوسط تكلفة الإصلاح
        avg_repair_cost = db.session.query(func.avg(Repair.cost)).filter(
            Repair.status == 'تم الإصلاح'
        ).scalar() or 0
        
        # طباعة التفاصيل
        print("Revenue Details:")
        print(f"Total Revenue: {total_revenue}")
        print(f"Today Revenue: {today_revenue}")
        print(f"Month Revenue: {month_revenue}")
        print(f"Average Repair Cost: {avg_repair_cost}")
        
        # عدد الإصلاحات المكتملة
        completed_repairs = Repair.query.filter(Repair.status == 'تم الإصلاح').count()
        print(f"Completed Repairs: {completed_repairs}")
        
    except Exception as e:
        print(f"Error in print_revenue_details: {str(e)}")

# استدعاء الدالة عند بدء التطبيق
print_customer_table_info()
print_repair_table_info()
print_revenue_details()

# تحميل إعدادات Discord
CONFIG_FILE = 'config.json'

def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"خطأ في قراءة ملف الإعدادات: {e}")
    return {"discord_webhook_url": "", "notifications_enabled": True}

def save_config(config):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"خطأ في حفظ ملف الإعدادات: {e}")

# تحميل الإعدادات عند بدء التطبيق
config = load_config()
discord_webhook_url = config.get('discord_webhook_url', '')
notifications_enabled = config.get('notifications_enabled', True)

def send_discord_notification(title, description, notification_type, color=0x00ff00):
    """إرسال إشعار إلى Discord وتسجيله"""
    status = 'نجاح'
    
    try:
        print(f"محاولة إرسال إشعار: {title}")
        print(f"Webhook URL: {discord_webhook_url}")
        print(f"Notifications Enabled: {notifications_enabled}")
        
        if notifications_enabled and discord_webhook_url:
            data = {
                "embeds": [{
                    "title": title.encode('utf-8').decode('utf-8'),
                    "description": description.encode('utf-8').decode('utf-8'),
                    "color": color,
                    "timestamp": datetime.utcnow().isoformat()
                }]
            }
            response = requests.post(discord_webhook_url, json=data)
            print(f"Response Status Code: {response.status_code}")
            
            if response.status_code != 204:
                status = 'فشل'
                print(f"فشل إرسال الإشعار: {response.text}")
        else:
            status = 'معطل'
            print("الإشعارات معطلة")
    except Exception as e:
        print(f"خطأ في إرسال إشعار Discord: {e}")
        status = 'فشل'
    
    # تسجيل الإشعار
    log = NotificationLog(
        title=title.encode('utf-8').decode('utf-8'),
        description=description.encode('utf-8').decode('utf-8'),
        type=notification_type,
        status=status
    )
    db.session.add(log)
    db.session.commit()
    print(f"تم تسجيل الإشعار: {title} - الحالة: {status}")

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# إعدادات الأمان
app.config['SESSION_COOKIE_SECURE'] = False  # السماح بالكوكيز على HTTP و HTTPS
app.config['REMEMBER_COOKIE_SECURE'] = False  # السماح بكوكيز تذكر الدخول على HTTP و HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True  # منع الوصول للكوكيز عبر JavaScript
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)  # مدة الجلسة 30 دقيقة

# إعدادات URL
app.config['PREFERRED_URL_SCHEME'] = 'https'  # تفضيل HTTPS ولكن السماح بـ HTTP

# إزالة التحويل الإجباري لـ HTTPS
# @app.before_request
# def before_request():
#     if not request.is_secure and app.env != 'development':
#         url = request.url.replace('http://', 'https://', 1)
#         return redirect(url, code=301)

@app.route('/login', methods=['GET'])
def login():
    if 'user' in session:
        return redirect(url_for('repairs_page'))
    return render_template('login.html')

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if username in USERS and USERS[username]['password'] == password:
        session['user'] = {
            'username': username,
            'role': USERS[username]['role']
        }
        return jsonify({
            'success': True,
            'redirect': url_for('repairs_page')
        })
    
    return jsonify({
        'success': False,
        'message': 'اسم المستخدم أو كلمة المرور غير صحيحة'
    }), 401

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Routes
@app.route('/')
@login_required
def index():
    return render_template('dashboard.html')

@app.route('/customers')
@login_required
def customers_page():
    return render_template('customers.html')

@app.route('/repairs')
@login_required
def repairs_page():
    return render_template('repairs.html')

@app.route('/repair/<int:repair_id>')
@login_required
def repair_details(repair_id):
    repair = Repair.query.get_or_404(repair_id)
    return render_template('repair_details.html', repair=repair)

@app.route('/api/customers', methods=['GET', 'POST'])
@login_required
def customers():
    if request.method == 'POST':
        data = request.json
        customer = Customer(
            name=data['name'],
            phone=data['phone'],
            workplace=data.get('workplace')  # استخدام get لتجنب الخطأ إذا لم يتم إرسال الحقل
        )
        db.session.add(customer)
        db.session.commit()
        send_discord_notification(
            "👤 عميل جديد",
            f"تمت إضافة عميل جديد:\nالاسم: {customer.name}\nرقم الهاتف: {customer.phone}",
            'عميل جديد'
        )
        return jsonify({'message': 'تم إضافة العميل بنجاح', 'id': customer.id})
    
    customers = Customer.query.all()
    return jsonify([{
        'id': c.id,
        'name': c.name,
        'phone': c.phone,
        'workplace': c.workplace,
        'repairs_count': len(c.repairs)
    } for c in customers])

@app.route('/api/customers/<int:customer_id>', methods=['DELETE'])
@login_required
def delete_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    name = customer.name  # حفظ اسم العميل قبل الحذف
    db.session.delete(customer)
    db.session.commit()
    
    # إرسال إشعار عند حذف عميل
    send_discord_notification(
        "❌ حذف عميل",
        f"تم حذف العميل:\nالاسم: {name}",
        'حذف عميل',
        color=0xff0000
    )
    return jsonify({'message': 'تم حذف العميل بنجاح'})

@app.route('/api/repairs', methods=['GET', 'POST'])
@login_required
def repairs():
    if request.method == 'POST':
        data = request.json
        try:
            # التحقق من وجود القيم الإلزامية
            if not all(key in data for key in ['customer_id', 'device_type', 'problem', 'cost']):
                return jsonify({'error': 'بيانات غير مكتملة'}), 400
            
            # التحقق من صحة القيم
            customer_id = int(data['customer_id'])
            device_type = str(data['device_type']).strip()
            problem = str(data['problem']).strip()
            cost = float(data['cost'])
            
            # التحقق من وجود العميل
            customer = Customer.query.get(customer_id)
            if not customer:
                return jsonify({'error': 'العميل غير موجود'}), 404
            
            # التحقق من صحة القيم
            if not device_type or not problem:
                return jsonify({'error': 'يجب إدخال نوع الجهاز والمشكلة'}), 400
            
            if cost < 0:
                return jsonify({'error': 'التكلفة يجب أن تكون رقمًا موجبًا'}), 400
            
            repair = Repair(
                customer_id=customer_id,
                device_type=device_type,
                problem=problem,
                cost=cost,
                date=datetime.utcnow(),  # تحديد التاريخ بشكل صريح
                status='قيد الانتظار'  # تحديد الحالة الافتراضية
            )
            db.session.add(repair)
            db.session.commit()
        
            # إرسال إشعار عند إضافة طلب صيانة جديد
            send_discord_notification(
                "🔧 طلب صيانة جديد",
                f"تم إضافة طلب صيانة جديد:\nالعميل: {customer.name}\nنوع الجهاز: {repair.device_type}\nالمشكلة: {repair.problem}\nالتكلفة: {repair.cost}",
                'طلب صيانة جديد',
                color=0x0000ff
            )
            return jsonify({'message': 'تمت إضافة طلب الصيانة بنجاح', 'repair_id': repair.id}), 201
        
        except (ValueError, TypeError) as e:
            db.session.rollback()
            return jsonify({'error': 'خطأ في تنسيق البيانات: ' + str(e)}), 400
        
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'حدث خطأ غير متوقع: ' + str(e)}), 500
    
    status = request.args.get('status')
    search_query = request.args.get('q', '').strip()
    
    # إنشاء الاستعلام الأساسي
    query = db.session.query(Repair).join(Customer)
    
    # تطبيق فلتر الحالة إذا تم تحديده
    if status:
        query = query.filter(Repair.status == status)
            
    # تطبيق البحث إذا تم إدخال كلمة بحث
    if search_query:
        search_filter = db.or_(
            Customer.name.ilike(f'%{search_query}%'),
            Customer.phone.ilike(f'%{search_query}%'),
            Repair.device_type.ilike(f'%{search_query}%'),
            Repair.problem.ilike(f'%{search_query}%')
        )
        query = query.filter(search_filter)
        
    repairs = query.order_by(Repair.date.desc()).all()
    return jsonify([{
        'id': repair.id,
        'customer_name': repair.customer.name,
        'customer_phone': repair.customer.phone,
        'device_type': repair.device_type,
        'problem': repair.problem,
        'cost': repair.cost,
        'status': repair.status,
        'date': repair.date.strftime('%Y-%m-%d %H:%M')
    } for repair in repairs])

@app.route('/api/repairs/<int:repair_id>', methods=['DELETE'])
@login_required
def delete_repair(repair_id):
    repair = Repair.query.get_or_404(repair_id)
    customer = repair.customer  # الحصول على بيانات العميل قبل الحذف
    device = repair.device_type  # حفظ نوع الجهاز قبل الحذف
    db.session.delete(repair)
    db.session.commit()
    
    # إرسال إشعار عند حذف طلب صيانة
    send_discord_notification(
        "❌ حذف طلب صيانة",
        f"تم حذف طلب الصيانة:\nالعميل: {customer.name}\nنوع الجهاز: {device}",
        'حذف طلب صيانة',
        color=0xff0000
    )
    return jsonify({'message': 'تم حذف الطلب بنجاح'})

@app.route('/api/repairs/<int:repair_id>', methods=['PUT'])
@login_required
def update_repair(repair_id):
    repair = Repair.query.get_or_404(repair_id)
    data = request.json
    
    if 'device_type' in data:
        repair.device_type = data['device_type']
    if 'problem' in data:
        repair.problem = data['problem']
    if 'cost' in data:
        repair.cost = float(data['cost'])
    
    db.session.commit()
    
    # إرسال إشعار عند تحديث بيانات طلب الصيانة
    changes = []
    if 'device_type' in data:
        changes.append(f"نوع الجهاز: {repair.device_type}")
    if 'problem' in data:
        changes.append(f"المشكلة: {repair.problem}")
    if 'cost' in data:
        changes.append(f"التكلفة: {repair.cost}")
    
    if changes:
        send_discord_notification(
            "📝 تحديث طلب صيانة",
            f"تم تحديث بيانات طلب الصيانة:\nالعميل: {repair.customer.name}\n" + "\n".join(changes),
            'تحديث طلب صيانة',
            color=0xffa500
        )
    
    return jsonify({'message': 'تم تحديث طلب الصيانة بنجاح'})

@app.route('/api/repairs/<int:repair_id>/status', methods=['PUT'])
@login_required
def update_repair_status(repair_id):
    data = request.json
    repair = Repair.query.get_or_404(repair_id)
    old_status = repair.status
    repair.status = data['status']
    db.session.commit()
    
    status_colors = {
        'قيد الانتظار': 0xffa500,  # برتقالي
        'جاري الصيانة': 0x0000ff,  # أزرق
        'تم الإصلاح': 0x00ff00,    # أخضر
        'تم التسليم': 0x4b0082     # بنفسجي
    }
    
    send_discord_notification(
        "🔧 تحديث حالة الصيانة",
        f"تم تحديث حالة الصيانة:\nرقم الطلب: {repair_id}\nالحالة: {old_status} ➡️ {repair.status}",
        'تحديث حالة الصيانة',
        color=status_colors.get(repair.status, 0x00ff00)
    )
    
    return jsonify({'message': 'تم تحديث حالة الطلب بنجاح'})

@app.route('/api/stats')
@login_required
def get_stats():
    today = date.today()
    
    total_customers = Customer.query.count()
    active_repairs = Repair.query.filter(Repair.status != 'تم التسليم').count()
    today_repairs = Repair.query.filter(
        func.date(Repair.date) == today
    ).count()
    total_revenue = db.session.query(db.func.sum(Repair.cost)).scalar() or 0
    
    latest_repairs = Repair.query.order_by(Repair.date.desc()).limit(5).all()
    latest_repairs_data = [{
        'customer_name': r.customer.name,
        'device_type': r.device_type,
        'status': r.status,
        'date': r.date.strftime('%Y-%m-%d')
    } for r in latest_repairs]
    
    status_stats = {}
    for repair in Repair.query.all():
        status_stats[repair.status] = status_stats.get(repair.status, 0) + 1
    
    return jsonify({
        'total_customers': total_customers,
        'active_repairs': active_repairs,
        'today_repairs': today_repairs,
        'total_revenue': total_revenue,
        'latest_repairs': latest_repairs_data,
        'status_stats': status_stats
    })

@app.route('/api/stats/revenue')
@login_required
def get_revenue_stats():
    # إحصائيات الإيرادات حسب حالة الصيانة
    status_revenue = db.session.query(
        Repair.status,
        db.func.sum(Repair.cost).label('total'),
        db.func.count(Repair.id).label('count')
    ).group_by(Repair.status).all()
    
    # إحصائيات الإيرادات حسب الفترة
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    daily_revenue = db.session.query(
        func.date(Repair.date).label('date'),
        db.func.sum(Repair.cost).label('total'),
        Repair.status,
        db.func.count(Repair.id).label('count')
    ).group_by(db.func.date(Repair.date), Repair.status)\
    .order_by(db.func.date(Repair.date).desc())\
    .limit(7).all()
    
    weekly_revenue = db.session.query(
        func.strftime('%Y-%W', Repair.date).label('week'),
        db.func.sum(Repair.cost).label('total'),
        Repair.status,
        db.func.count(Repair.id).label('count')
    ).group_by(db.func.strftime('%Y-%W', Repair.date), Repair.status)\
    .order_by(db.func.strftime('%Y-%W', Repair.date).desc())\
    .limit(4).all()
    
    monthly_revenue = db.session.query(
        func.strftime('%Y-%m', Repair.date).label('month'),
        db.func.sum(Repair.cost).label('total'),
        Repair.status,
        db.func.count(Repair.id).label('count')
    ).group_by(db.func.strftime('%Y-%m', Repair.date), Repair.status)\
    .order_by(db.func.strftime('%Y-%m', Repair.date).desc())\
    .limit(6).all()
    
    return jsonify({
        'status': [{
            'status': r.status,
            'total': float(r.total),
            'count': r.count
        } for r in status_revenue],
        'daily': [{
            'date': str(r.date),
            'total': float(r.total),
            'status': r.status,
            'count': r.count
        } for r in daily_revenue],
        'weekly': [{
            'week': r.week,
            'total': float(r.total),
            'status': r.status,
            'count': r.count
        } for r in weekly_revenue],
        'monthly': [{
            'month': r.month,
            'total': float(r.total),
            'status': r.status,
            'count': r.count
        } for r in monthly_revenue]
    })

@app.route('/api/stats/devices')
@login_required
def get_device_stats():
    # إحصائيات أنواع الأجهزة
    top_devices = db.session.query(
        Repair.device_type,
        db.func.count(Repair.id).label('count'),
        db.func.sum(Repair.cost).label('total_revenue')
    ).group_by(Repair.device_type)\
    .order_by(db.func.count(Repair.id).desc())\
    .limit(5).all()
    
    return jsonify([{
        'device_type': d.device_type,
        'count': d.count,
        'total_revenue': float(d.total_revenue)
    } for d in top_devices])

@app.route('/api/stats/customers/details')
@login_required
def get_customer_details():
    try:
        # حساب العملاء الجدد اليوم
        today = datetime.now().date()
        
        # التحقق من وجود حقل التاريخ
        if not hasattr(Customer, 'date'):
            # إذا لم يكن هناك حقل date، استخدم id كبديل
            new_customers_today = Customer.query.filter(Customer.id > 0).count()
            new_customers_this_month = new_customers_today
        else:
            new_customers_today = Customer.query.filter(
                func.date(Customer.date) == today
            ).count()
            
            # حساب العملاء الجدد هذا الشهر
            first_day_of_month = today.replace(day=1)
            new_customers_this_month = Customer.query.filter(
                func.date(Customer.date) >= first_day_of_month
            ).count()
        
        # حساب العملاء النشطين (لديهم صيانة نشطة)
        active_customers = db.session.query(Customer).join(Repair).filter(
            Repair.status.in_(['قيد الانتظار', 'جاري الصيانة'])
        ).distinct().count()
        
        # طباعة المعلومات للتأكد
        print(f"New Today: {new_customers_today}")
        print(f"New This Month: {new_customers_this_month}")
        print(f"Active Customers: {active_customers}")
        
        return jsonify({
            'new_today': new_customers_today,
            'new_this_month': new_customers_this_month,
            'active_customers': active_customers
        })
    except Exception as e:
        # طباعة أي أخطاء للتشخيص
        print(f"Error in get_customer_details: {str(e)}")
        return jsonify({
            'error': str(e),
            'new_today': 0,
            'new_this_month': 0,
            'active_customers': 0
        }), 500

@app.route('/api/stats/repairs/details')
@login_required
def get_repair_details():
    try:
        today = datetime.now().date()
        
        # التحقق من وجود حقل التاريخ
        if not hasattr(Repair, 'date'):
            # إذا لم يكن هناك حقل date، استخدم id كبديل
            new_repairs_today = Repair.query.filter(Repair.id > 0).count()
            in_progress_repairs = new_repairs_today
            pending_repairs = new_repairs_today
            completed_today = new_repairs_today
        else:
            # الصيانات الجديدة اليوم
            new_repairs_today = Repair.query.filter(
                func.date(Repair.date) == today
            ).count()
            
            # الصيانات قيد التنفيذ
            in_progress_repairs = Repair.query.filter(
                Repair.status == 'جاري الصيانة'
            ).count()
            
            # الصيانات المعلقة
            pending_repairs = Repair.query.filter(
                Repair.status == 'قيد الانتظار'
            ).count()
            
            # الصيانات المكتملة اليوم
            completed_today = Repair.query.filter(
                func.date(Repair.date) == today,
                Repair.status == 'تم الإصلاح'
            ).count()
        
        # حساب نسبة الإنجاز
        completion_rate = (completed_today / new_repairs_today * 100) if new_repairs_today > 0 else 0
        
        # طباعة المعلومات للتأكد
        print(f"New Repairs Today: {new_repairs_today}")
        print(f"In Progress Repairs: {in_progress_repairs}")
        print(f"Pending Repairs: {pending_repairs}")
        print(f"Completed Today: {completed_today}")
        print(f"Completion Rate: {completion_rate:.2f}%")
        
        return jsonify({
            'new_today': new_repairs_today,
            'in_progress': in_progress_repairs,
            'pending': pending_repairs,
            'completed_today': completed_today,
            'completion_rate': round(completion_rate, 2)
        })
    except Exception as e:
        # طباعة أي أخطاء للتشخيص
        print(f"Error in get_repair_details: {str(e)}")
        return jsonify({
            'error': str(e),
            'new_today': 0,
            'in_progress': 0,
            'pending': 0,
            'completed_today': 0,
            'completion_rate': 0
        }), 500

@app.route('/api/stats/revenue/details')
@login_required
def get_revenue_details():
    try:
        today = datetime.now().date()
        
        # التحقق من وجود حقل التاريخ
        if not hasattr(Repair, 'date'):
            # إذا لم يكن هناك حقل date، استخدم id كبديل
            today_revenue = 0
            month_revenue = 0
            avg_repair_cost = 0
        else:
            # إيرادات اليوم
            today_revenue = db.session.query(func.sum(Repair.cost)).filter(
                func.date(Repair.date) == today,
                Repair.status == 'تم الإصلاح'
            ).scalar() or 0
            
            # إيرادات الشهر
            first_day_of_month = today.replace(day=1)
            month_revenue = db.session.query(func.sum(Repair.cost)).filter(
                func.date(Repair.date) >= first_day_of_month,
                Repair.status == 'تم الإصلاح'
            ).scalar() or 0
            
            # متوسط تكلفة الإصلاح
            avg_repair_cost = db.session.query(func.avg(Repair.cost)).filter(
                Repair.status == 'تم الإصلاح'
            ).scalar() or 0
        
        # طباعة المعلومات للتأكد
        print(f"Today Revenue: {today_revenue}")
        print(f"Month Revenue: {month_revenue}")
        print(f"Average Repair Cost: {avg_repair_cost}")
        
        return jsonify({
            'today_revenue': round(today_revenue, 2),
            'month_revenue': round(month_revenue, 2),
            'avg_repair_cost': round(avg_repair_cost, 2)
        })
    except Exception as e:
        # طباعة أي أخطاء للتشخيص
        print(f"Error in get_revenue_details: {str(e)}")
        return jsonify({
            'error': str(e),
            'today_revenue': 0,
            'month_revenue': 0,
            'avg_repair_cost': 0
        }), 500

@app.route('/api/dashboard/stats')
@login_required
def get_dashboard_stats():
    try:
        # إحصائيات العملاء
        total_customers = Customer.query.count()
        
        # إحصائيات الإصلاحات
        total_repairs = Repair.query.count()
        active_repairs = Repair.query.filter(Repair.status.in_(['قيد الانتظار', 'جاري الصيانة'])).count()
        
        # إحصائيات اليوم
        today = datetime.now().date()
        today_repairs = Repair.query.filter(
            func.date(Repair.date) == today
        ).count()
        
        # حساب الإيرادات
        completed_repairs = Repair.query.filter_by(status='تم الإصلاح').all()
        total_revenue = sum(repair.cost for repair in completed_repairs if repair.cost)
        
        return jsonify({
            'total_customers': total_customers,
            'total_repairs': total_repairs,
            'active_repairs': active_repairs,
            'today_repairs': today_repairs,
            'total_revenue': total_revenue
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/repair-stats')
@login_required
def get_repair_stats():
    try:
        repairs = Repair.query.all()
        stats = {
            'تم الإصلاح': 0,
            'تم التسليم': 0,
            'جاري الصيانة': 0,
            'قيد الانتظار': 0
        }
        
        for repair in repairs:
            if repair.status in stats:
                stats[repair.status] += 1
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/revenue')
@login_required
def get_revenue_data():
    try:
        period = request.args.get('period', 'daily')
        status = request.args.get('status', None)  # إضافة فلتر حسب الحالة
        today = datetime.now().date()
        
        if period == 'daily':
            # البيانات اليومية للأسبوع الحالي
            start_date = today - timedelta(days=6)
            query = Repair.query.filter(func.date(Repair.date) >= start_date)
            
            if status:
                query = query.filter(Repair.status == status)
            
            repairs = query.all()
            
            daily_revenue = defaultdict(lambda: {'total': 0.0, 'count': 0})
            for repair in repairs:
                date_str = repair.date.strftime('%Y-%m-%d')
                daily_revenue[date_str]['total'] += repair.cost or 0
                daily_revenue[date_str]['count'] += 1
            
            # تحويل التواريخ إلى أيام الأسبوع بالعربية
            days_arabic = ['السبت', 'الأحد', 'الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة']
            labels = []
            data = []
            counts = []
            
            for i in range(7):
                date = start_date + timedelta(days=i)
                date_str = date.strftime('%Y-%m-%d')
                labels.append(days_arabic[date.weekday()])
                data.append(daily_revenue[date_str]['total'])
                counts.append(daily_revenue[date_str]['count'])
            
        elif period == 'weekly':
            # البيانات الأسبوعية للشهر الحالي
            start_date = today - timedelta(weeks=4)
            query = Repair.query.filter(func.date(Repair.date) >= start_date)
            
            if status:
                query = query.filter(Repair.status == status)
            
            repairs = query.all()
            
            weekly_revenue = defaultdict(lambda: {'total': 0.0, 'count': 0})
            for repair in repairs:
                week = repair.date.strftime('%Y-%W')
                weekly_revenue[week]['total'] += repair.cost or 0
                weekly_revenue[week]['count'] += 1
            
            labels = ['الأسبوع ' + str(i+1) for i in range(4)]
            data = []
            counts = []
            
            current_week = datetime.now().strftime('%Y-%W')
            for i in range(4):
                week = (datetime.now() - timedelta(weeks=i)).strftime('%Y-%W')
                data.append(weekly_revenue[week]['total'])
                counts.append(weekly_revenue[week]['count'])
            
            # عكس الترتيب ليكون من الأقدم للأحدث
            labels.reverse()
            data.reverse()
            counts.reverse()
            
        elif period == 'monthly':
            # البيانات الشهرية للستة أشهر الماضية
            start_date = today - timedelta(days=180)
            query = Repair.query.filter(func.date(Repair.date) >= start_date)
            
            if status:
                query = query.filter(Repair.status == status)
            
            repairs = query.all()
            
            monthly_revenue = defaultdict(lambda: {'total': 0.0, 'count': 0})
            for repair in repairs:
                month = repair.date.strftime('%Y-%m')
                monthly_revenue[month]['total'] += repair.cost or 0
                monthly_revenue[month]['count'] += 1
            
            # الأشهر بالعربية
            months_arabic = ['يناير', 'فبراير', 'مارس', 'إبريل', 'مايو', 'يونيو', 
                           'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر']
            
            labels = []
            data = []
            counts = []
            
            for i in range(6):
                date = today - timedelta(days=30*i)
                month = date.strftime('%Y-%m')
                labels.append(months_arabic[date.month - 1])
                data.append(monthly_revenue[month]['total'])
                counts.append(monthly_revenue[month]['count'])
            
            # عكس الترتيب ليكون من الأقدم للأحدث
            labels.reverse()
            data.reverse()
            counts.reverse()
        
        return jsonify({
            'labels': labels,
            'data': data,
            'counts': counts,
            'period': period,
            'status': status
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/recent-repairs')
@login_required
def get_recent_repairs():
    try:
        # الحصول على آخر 10 طلبات صيانة
        recent_repairs = Repair.query.order_by(Repair.date.desc()).limit(10).all()
        
        repairs_list = []
        for repair in recent_repairs:
            repairs_list.append({
                'customer_name': repair.customer.name,
                'device_type': repair.device_type,
                'problem': repair.problem,
                'status': repair.status,
                'date': repair.date.strftime('%Y-%m-%d %H:%M'),
                'cost': repair.cost
            })
        
        return jsonify(repairs_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/notifications/log')
@login_required
def notifications_log():
    """صفحة سجل الإشعارات"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    logs = NotificationLog.query.order_by(NotificationLog.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    
    return render_template('notifications_log.html', logs=logs)

@app.route('/api/notifications/stats')
@login_required
def get_notifications_stats():
    """استرجاع إحصائيات الإشعارات"""
    from sqlalchemy import func
    
    # إجمالي الإشعارات
    total_notifications = NotificationLog.query.count()
    
    # إحصائيات حسب الحالة
    status_stats = db.session.query(
        NotificationLog.status, 
        func.count(NotificationLog.id)
    ).group_by(NotificationLog.status).all()
    
    status_dict = {status: count for status, count in status_stats}
    
    # إحصائيات حسب النوع
    type_stats = db.session.query(
        NotificationLog.type, 
        func.count(NotificationLog.id)
    ).group_by(NotificationLog.type).all()
    
    type_dict = {type_name: count for type_name, count in type_stats}
    
    # إحصائيات يومية
    daily_stats = db.session.query(
        func.date(NotificationLog.timestamp).label('date'), 
        func.count(NotificationLog.id)
    ).group_by('date').order_by('date').all()
    
    daily_dict = {str(date): count for date, count in daily_stats}
    
    return jsonify({
        'total': total_notifications,
        'by_status': status_dict,
        'by_type': type_dict,
        'daily': daily_dict
    })

# مسار صفحة الإعدادات
@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html')

# API لحفظ الإعدادات
@app.route('/api/settings', methods=['GET', 'POST'])
@login_required
def handle_settings():
    if request.method == 'POST':
        # حفظ الإعدادات في قاعدة البيانات
        settings_data = request.json
        try:
            # يمكنك تخزين الإعدادات في قاعدة البيانات هنا
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    else:
        # استرجاع الإعدادات الحالية
        settings = {
            'darkMode': False,
            'notifications': True,
            'paperSize': 'A4',
            'printLogo': True,
            'companyName': 'مركز الصيانة',
            'phone': '0512345678',
            'address': 'الرياض، المملكة العربية السعودية'
        }
        return jsonify(settings)

@app.route('/api/database/export')
@login_required
def export_database():
    try:
        # جمع البيانات من جميع الجداول
        data = {
            'customers': [customer.to_dict() for customer in Customer.query.all()],
            'repairs': [repair.to_dict() for repair in Repair.query.all()]
        }
        
        # تحويل التواريخ إلى نص
        for repair in data['repairs']:
            if repair.get('date'):
                repair['date'] = repair['date'].strftime('%Y-%m-%d %H:%M:%S')
        
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/database/import', methods=['POST'])
@login_required
def import_database():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'لم يتم تحديد ملف'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'لم يتم تحديد ملف'}), 400
            
        if not file.filename.endswith('.json'):
            return jsonify({'success': False, 'error': 'يجب أن يكون الملف بصيغة JSON'}), 400
            
        # قراءة البيانات من الملف
        data = json.loads(file.read())
        
        try:
            # حذف البيانات الحالية
            Repair.query.delete()
            Customer.query.delete()
            NotificationLog.query.delete()
            db.session.commit()
            
            # إضافة العملاء
            for customer_data in data.get('customers', []):
                customer = Customer(
                    name=customer_data['name'],
                    phone=customer_data.get('phone'),
                    workplace=customer_data.get('workplace')
                )
                db.session.add(customer)
            
            db.session.commit()  # حفظ العملاء أولاً للحصول على الـ IDs
            
            # إضافة طلبات الصيانة
            for repair_data in data.get('repairs', []):
                date = datetime.strptime(repair_data['date'], '%Y-%m-%d %H:%M:%S') if repair_data.get('date') else None
                repair = Repair(
                    customer_id=repair_data['customer_id'],
                    device_type=repair_data['device_type'],
                    problem=repair_data['problem'],
                    cost=repair_data.get('cost'),
                    status=repair_data.get('status', 'قيد الانتظار'),
                    date=date
                )
                db.session.add(repair)
            
            db.session.commit()
            return jsonify({'success': True})
            
        except Exception as e:
            db.session.rollback()
            raise e
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# إضافة مسارات API لإدارة المستخدمين
@app.route('/api/user/current')
@login_required
def get_current_user():
    return jsonify({
        'username': session['user']['username'],
        'role': session['user']['role']
    })

@app.route('/api/users')
@login_required
def get_users():
    # التحقق من أن المستخدم هو مدير
    if session['user']['role'] != 'admin':
        return jsonify({'error': 'غير مصرح لك بالوصول'}), 403
    
    return jsonify([{
        'username': username,
        'role': user_data['role']
    } for username, user_data in USERS.items()])

@app.route('/api/user/password', methods=['POST'])
@login_required
def change_password():
    data = request.get_json()
    new_password = data.get('newPassword')
    username = session['user']['username']
    
    # التحقق من طول كلمة المرور
    if len(new_password) < 6:
        return jsonify({
            'success': False,
            'message': 'يجب أن تكون كلمة المرور 6 أحرف على الأقل'
        }), 400
    
    # تحديث كلمة المرور
    USERS[username]['password'] = new_password
    
    return jsonify({
        'success': True,
        'message': 'تم تغيير كلمة المرور بنجاح'
    })

@app.route('/api/user/reset-password', methods=['POST'])
@login_required
def reset_user_password():
    # التحقق من أن المستخدم هو مدير
    if session['user']['role'] != 'admin':
        return jsonify({'error': 'غير مصرح لك بالوصول'}), 403
    
    data = request.get_json()
    username = data.get('username')
    
    if username not in USERS:
        return jsonify({
            'success': False,
            'message': 'المستخدم غير موجود'
        }), 404
    
    # إنشاء كلمة مرور جديدة عشوائية
    import random
    import string
    new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    
    # تحديث كلمة المرور
    USERS[username]['password'] = new_password
    
    return jsonify({
        'success': True,
        'newPassword': new_password,
        'message': 'تم إعادة تعيين كلمة المرور بنجاح'
    })

@app.route('/accounts')
@login_required
def accounts_page():
    return render_template('accounts.html')

if __name__ == '__main__':
    # تشغيل الخادم على المنفذين 80 (HTTP) و 443 (HTTPS)
    from werkzeug.serving import run_simple
    
    # التحقق من وجود شهادات SSL
    ssl_context = None
    if os.environ.get('FLASK_ENV') == 'production' and os.path.exists('cert.pem') and os.path.exists('key.pem'):
        ssl_context = ('cert.pem', 'key.pem')
    
    # تشغيل التطبيق
    if os.environ.get('FLASK_ENV') == 'production':
        # في بيئة الإنتاج، استخدم gunicorn
        from gunicorn.app.base import BaseApplication

        class FlaskApplication(BaseApplication):
            def __init__(self, app, options=None):
                self.options = options or {}
                self.application = app
                super().__init__()

            def load_config(self):
                for key, value in self.options.items():
                    self.cfg.set(key, value)

            def load(self):
                return self.application

        options = {
            'bind': ['0.0.0.0:80', '0.0.0.0:443'],
            'workers': 4,
            'certfile': 'cert.pem' if ssl_context else None,
            'keyfile': 'key.pem' if ssl_context else None
        }
        
        FlaskApplication(app, options).run()
    else:
        # في بيئة التطوير، استخدم خادم Flask المدمج
        app.run(host='0.0.0.0', port=5000, debug=True)