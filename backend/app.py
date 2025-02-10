import os
import json
import base64
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://mecit:mct123@127.0.0.1:3306/testdb'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

class TestSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    answers = db.Column(db.Text, nullable=False)
    score = db.Column(db.Float, nullable=False)
    submission_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    test_title = db.Column(db.String(100), nullable=False)  # Yeni eklenen alan

class PageVisit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    visit_date = db.Column(db.Date, nullable=False)
    visit_count = db.Column(db.Integer, default=1)

DEFAULT_OPTIONS = ["A", "B", "C", "D"]

DATA_DIR = os.path.join(os.getcwd(), "data")
TEST_IMAGES_DIR = os.path.join(DATA_DIR, "test_images")
ANSWERS_FILE = os.path.join(DATA_DIR, "answers.json")

def load_answers():
    if os.path.exists(ANSWERS_FILE):
        with open(ANSWERS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('title', ''), data.get('answers', {})
    return '', {}

def load_questions():
    questions = []
    test_title, answers = load_answers()
    try:
        image_files = [f for f in os.listdir(TEST_IMAGES_DIR)
                       if os.path.isfile(os.path.join(TEST_IMAGES_DIR, f)) and
                       f.lower().endswith(('.png', '.jpg', '.jpeg'))]

        for idx, filename in enumerate(sorted(image_files), start=1):
            image_path = os.path.join(TEST_IMAGES_DIR, filename)
            with open(image_path, "rb") as img_file:
                img_base64 = base64.b64encode(img_file.read()).decode('utf-8')

            correct_option = answers.get(f"q{idx}.png", 0)

            question = {
                "id": idx,
                "text": f"Soru {idx}",
                "image_base64": img_base64,
                "options": DEFAULT_OPTIONS,
                "correct_option": correct_option
            }
            questions.append(question)
    except Exception as e:
        print(f"Error loading questions: {str(e)}")
        return [], ''
    return questions, test_title

def record_visit():
    today = date.today()
    visit = PageVisit.query.filter_by(visit_date=today).first()
    
    if visit:
        visit.visit_count += 1
    else:
        visit = PageVisit(visit_date=today, visit_count=1)
        db.session.add(visit)
    
    try:
        db.session.commit()
    except:
        db.session.rollback()

@app.route('/stats', methods=['GET'])
def get_stats():
    try:
        today = date.today()
        today_visits = PageVisit.query.filter_by(visit_date=today).first()
        daily_visitors = today_visits.visit_count if today_visits else 0
        
        total_visitors = db.session.query(db.func.sum(PageVisit.visit_count)).scalar() or 0
        
        return jsonify({
            "daily_visitors": daily_visitors,
            "total_visitors": total_visitors
        })
    except Exception as e:
        print(f"Error getting stats: {str(e)}")
        return jsonify({"error": "Failed to get statistics"}), 500

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400
    
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 400
    
    user = User(
        username=username,
        password_hash=generate_password_hash(password)
    )
    
    try:
        db.session.add(user)
        db.session.commit()
        return jsonify({"message": "User registered successfully"}), 201
    except:
        db.session.rollback()
        return jsonify({"error": "Registration failed"}), 500

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    user = User.query.filter_by(username=username).first()
    
    if user and check_password_hash(user.password_hash, password):
        record_visit()  # Ziyaret kaydı
        return jsonify({"message": "Login successful", "username": username}), 200
    
    return jsonify({"error": "Invalid username or password"}), 401

@app.route('/user-tests/<username>', methods=['GET'])
def get_user_tests(username):
    tests = TestSubmission.query.filter_by(username=username)\
        .order_by(TestSubmission.submission_date.desc()).all()
    
    test_history = []
    for test in tests:
        test_history.append({
            "id": test.id,
            "score": test.score,
            "submission_date": test.submission_date.strftime("%Y-%m-%d %H:%M:%S"),
            "answers": json.loads(test.answers),
            "test_title": test.test_title  # Yeni eklenen alan
        })
    
    return jsonify(test_history)

@app.route('/')
def home():
    record_visit()  # Ziyaret kaydı
    return jsonify({"message": "Test API is running", "status": "ok"})

@app.route('/test', methods=['GET'])
def get_test():
    questions, test_title = load_questions()
    if not questions:
        return jsonify({"error": "Failed to load questions"}), 500
    return jsonify({"questions": questions, "test_title": test_title})

@app.route('/submit', methods=['POST'])
def submit():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    data = request.get_json()
    if not data or 'username' not in data or 'answers' not in data:
        return jsonify({"error": "Missing required fields"}), 400

    username = data.get("username")
    user_answers = data.get("answers", {})

    questions, test_title = load_questions()

    correct = 0
    wrong = 0
    blank = 0
    details = []
    correct_questions = []
    wrong_questions = []

    for q in questions:
        qid = str(q["id"])
        answer = user_answers.get(qid)

        if answer is None or answer == "0":
            blank += 1
            details.append({"question_id": qid, "status": "blank"})
        else:
            try:
                answer = int(answer)
                if answer == q["correct_option"]:
                    correct += 1
                    correct_questions.append(qid)
                    details.append({"question_id": qid, "status": "correct"})
                else:
                    wrong += 1
                    wrong_questions.append(qid)
                    details.append({"question_id": qid, "status": "wrong"})
            except ValueError:
                wrong += 1
                wrong_questions.append(qid)
                details.append({"question_id": qid, "status": "wrong"})

    net = correct - (wrong / 3.0)

    try:
        submission = TestSubmission(
            username=username,
            answers=json.dumps(user_answers),
            score=net,
            test_title=test_title  # Yeni eklenen alan
        )
        db.session.add(submission)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Database error: {str(e)}")
        return jsonify({"error": "Failed to save submission"}), 500

    return jsonify({
        "message": "Test tamamlandı!",
        "username": username,
        "correct": correct,
        "wrong": wrong,
        "blank": blank,
        "net": round(net, 2),
        "correct_questions": correct_questions,
        "wrong_questions": wrong_questions,
        "details": details,
        "test_title": test_title  # Yeni eklenen alan
    })

if __name__ == '__main__':
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            print(f"Database initialization error: {str(e)}")

    app.run(host="0.0.0.0", port=5000, debug=True)