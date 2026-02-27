from flask import Flask, request, jsonify, render_template
import uuid
from datetime import datetime

app = Flask(__name__)

# Oddiy xotirada saqlash (haqiqiy loyihada DB ishlatish kerak)
# Tuzilishi: {id: str, data: dict, created_at: str, status: 'pending'|'printed'}
print_jobs = []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/print', methods=['POST'])
def add_print_job():
    """Saytdan yangi chek qo'shish"""
    data = request.json
    job = {
        'id': str(uuid.uuid4()),
        'data': data,
        'created_at': datetime.now().isoformat(),
        'status': 'pending'
    }
    print_jobs.append(job)
    print(f"➕ Yangi vazifa qo'shildi: {job['id']}")
    return jsonify({'status': 'ok', 'job_id': job['id']}), 201

@app.route('/api/poll', methods=['GET'])
def poll_print_jobs():
    """Agent (PC) uchun: yangi vazifa bormi?"""
    global print_jobs
    
    # Faqat 'pending' statusdagi eng eski vazifani olamiz
    pending_jobs = [j for j in print_jobs if j['status'] == 'pending']
    
    if not pending_jobs:
        return jsonify({'job': None})
    
    # FIFO (First In First Out)
    job = pending_jobs[0]
    
    # Vazifani "jarayonda" deb belgilaymiz yoki ro'yxatdan o'chiramiz 
    # (Hozircha oddiylik uchun darrov o'chiramiz yoki statusni o'zgartiramiz)
    job['status'] = 'processing'
    
    return jsonify({'job': job})

@app.route('/api/ack/<job_id>', methods=['POST'])
def acknowledge_job(job_id):
    """Agent tasdiqlaydi: Chek chiqdi"""
    global print_jobs
    # Ro'yxatdan o'chirib tashlaymiz
    print_jobs = [j for j in print_jobs if j['id'] != job_id]
    print(f"✅ Vazifa bajarildi va o'chirildi: {job_id}")
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    # 0.0.0.0 - tarmoqdagi boshqa kompyuterlar ham ulana olishi uchun
    app.run(host='0.0.0.0', port=5000, debug=True)
