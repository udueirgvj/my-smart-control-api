from flask import Flask, jsonify, request
from datetime import datetime, timedelta
import json
import os

app = Flask(__name__)

# مسار ملف حفظ البيانات المؤقت لضمان عدم ضياع التحديثات
DATA_FILE = '/tmp/database.json'

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"requests": {}, "active_users": {}}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 1. مسار للمشترك: يرسل اسمه لطلب تفعيل الخدمة
@app.route('/api/request_access', methods=['POST'])
def request_access():
    data = request.json
    username = data.get('username')
    
    if not username:
        return jsonify({"error": "الرجاء إدخال اسم المستخدم"}), 400
        
    db = load_data()
    db["requests"][username] = {
        "request_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "pending"
    }
    save_data(db)
    return jsonify({"message": "تم إرسال طلبك بنجاح إلى المالك، انتظر التفعيل!"}), 200

# 2. مسار للمالك: يستعرض كل الطلبات المعلقة التي أرسلها المشتركون
@app.route('/api/owner/view_requests', methods=['GET'])
def view_requests():
    db = load_data()
    return jsonify({"pending_requests": db["requests"]}), 200

# 3. مسار للمالك: يوافق على الطلب ويحدد المدة (بالأيام مثلاً)
@app.route('/api/owner/approve', methods=['POST'])
def approve_user():
    data = request.json
    username = data.get('username')
    days = data.get('days', 1)  # الافتراضي يوم واحد إذا لم يحدد المالك
    
    db = load_data()
    if username not in db["requests"]:
        return jsonify({"error": "هذا الطلب غير موجود"}), 404
        
    # حساب تاريخ انتهاء الصلاحية بناءً على المدة التي حددها المالك
    expiry_time = datetime.now() + timedelta(days=int(days))
    
    # نقل المستخدم من الطلبات المعلقة إلى المشتركين الفعالين
    db["active_users"][username] = {
        "expiry_date": expiry_time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "active"
    }
    # مسح الطلب من قائمة المعلقات بعد الموافقة
    del db["requests"][username]
    
    save_data(db)
    return jsonify({"message": f"تم تفعيل حساب {username} بنجاح لمدة {days} يوم!"}), 200

# 4. مسار لفحص حالة المشترك (الجهة الخلفية للتطبيق أو النفق للتأكد هل وقته انتهى أم لا)
@app.route('/api/check_access', methods=['GET'])
def check_access():
    username = request.args.get('username')
    db = load_data()
    
    if username not in db["active_users"]:
        return jsonify({"status": "no_access", "message": "ليس لديك صلاحية وصول أو انتهت مدتك"}), 403
        
    user_info = db["active_users"][username]
    expiry_date = datetime.strptime(user_info["expiry_date"], "%Y-%m-%d %H:%M:%S")
    
    # التحقق إذا كانت المدة قد انتهت حالياً
    if datetime.now() > expiry_date:
        db["active_users"][username]["status"] = "expired"
        save_data(db)
        return jsonify({"status": "expired", "message": "انتهت المدة المحددة لك من قبل المالك!"}), 403
        
    return jsonify({
        "status": "active",
        "message": "الوصول متاح",
        "expires_at": user_info["expiry_date"]
    }), 200

@app.route('/')
def home():
    return "منظومة تحكم المالك الذكية تعمل بنجاح وأمان على Vercel!"

