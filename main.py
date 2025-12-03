import os
import uuid
from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///dance.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = "uploads"

os.makedirs("uploads", exist_ok=True)
db = SQLAlchemy(app)

# MODELS
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    password_hash = db.Column(db.String(200))
    school = db.Column(db.String(80))
    token = db.Column(db.String(100))

class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200))
    title = db.Column(db.String(200))
    uploader_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    school = db.Column(db.String(80))

def allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ["mp4", "mov", "avi", "webm"]

def get_user():
    token = request.headers.get("Authorization")
    if not token:
        return None
    return User.query.filter_by(token=token).first()

# ROUTES
@app.route("/register", methods=["POST"])
def register():
    data = request.json
    if User.query.filter_by(username=data["username"]).first():
        return jsonify({"error": "username exists"}), 400
    user = User(
        username=data["username"],
        password_hash=generate_password_hash(data["password"]),
        school=data["school"],
        token=uuid.uuid4().hex
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({"token": user.token})

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    user = User.query.filter_by(username=data["username"]).first()
    if not user or not check_password_hash(user.password_hash, data["password"]):
        return jsonify({"error": "Invalid"}), 401
    return jsonify({"token": user.token})

@app.route("/upload", methods=["POST"])
def upload():
    user = get_user()
    if not user:
        return jsonify({"error": "No token"}), 401

    file = request.files.get("file")
    if not file or not allowed(file.filename):
        return jsonify({"error": "Bad file"}), 400

    filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
    file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

    video = Video(filename=filename, title=request.form.get("title", ""), uploader_id=user.id, school=user.school)
    db.session.add(video)
    db.session.commit()

    return jsonify({"message": "Uploaded!"})

@app.route("/videos", methods=["GET"])
def list_videos():
    videos = Video.query.all()
    return jsonify([{
        "id": v.id,
        "title": v.title,
        "filename": v.filename,
        "url": f"/play/{v.id}"
    } for v in videos])

@app.route("/play/<int:video_id>")
def play(video_id):
    video = Video.query.get(video_id)
    if not video:
        return "Not found", 404
    return send_from_directory(app.config["UPLOAD_FOLDER"], video.filename)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000)