import os
import base64
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, jsonify
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash

# -------------------- Flask Setup --------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = "secretkey"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB upload limit

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login_page"

# -------------------- Models --------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    has_voted = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)

class Candidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    candidate = db.Column(db.String(100))
    photo_path = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# -------------------- Initialize Database --------------------
with app.app_context():
    db.create_all()
    os.makedirs("static/photos", exist_ok=True)

    # Default admin creation
    if not User.query.filter_by(username="admin").first():
        admin = User(
            username="admin",
            password=generate_password_hash("admin123", method="pbkdf2:sha256"),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()

# -------------------- Routes --------------------
@app.route("/")
def home():
    return redirect(url_for("login_page"))

# ---------- Authentication ----------
@app.route("/register", methods=["GET", "POST"])
def register_page():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if User.query.filter_by(username=username).first():
            flash("Username already exists!")
            return redirect(url_for("register_page"))

        hashed_pw = generate_password_hash(password, method="pbkdf2:sha256")
        new_user = User(username=username, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful! Please log in.")
        return redirect(url_for("login_page"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()

        if not user or not check_password_hash(user.password, password):
            flash("Invalid username or password")
            return redirect(url_for("login_page"))

        login_user(user)
        if user.is_admin:
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("vote_page"))

    return render_template("login.html")

@app.route("/logout")
@login_required
def logout_page():
    logout_user()
    return redirect(url_for("login_page"))

# ---------- Voting ----------
@app.route("/vote", methods=["GET", "POST"])
@login_required
def vote_page():
    if current_user.is_admin:
        return redirect(url_for("admin_dashboard"))

    if current_user.has_voted:
        return render_template("vote_done.html")

    candidates = Candidate.query.all()

    if request.method == "POST":
        selected_candidate = request.form.get("candidate")
        photo_data = request.form.get("photo")

        if not photo_data:
            flash("Face photo required for voting!")
            return redirect(url_for("vote_page"))

        # Save photo
        header, encoded = photo_data.split(",", 1)
        img_bytes = base64.b64decode(encoded)
        photo_path = f"static/photos/user_{current_user.id}.png"
        with open(photo_path, "wb") as f:
            f.write(img_bytes)

        # Save vote
        vote = Vote(
            user_id=current_user.id,
            candidate=selected_candidate,
            photo_path=f"photos/user_{current_user.id}.png"
        )
        current_user.has_voted = True
        db.session.add(vote)
        db.session.commit()
        flash("Vote submitted successfully!")
        return redirect(url_for("vote_page"))

    return render_template("vote.html", candidates=candidates)

# ---------- Voter Management ----------
@app.route("/voters")
@login_required
def manage_voters():
    if not current_user.is_admin:
        flash("You are not authorized to access this page!")
        return redirect(url_for("vote_page"))

    voters = User.query.all()
    return render_template("voters.html", voters=voters)

# ---------- Admin Dashboard ----------
@app.route("/admin")
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash("You are not authorized to access this page!")
        return redirect(url_for("vote_page"))

    votes = Vote.query.all()
    count = {}
    for v in votes:
        count[v.candidate] = count.get(v.candidate, 0) + 1

    voters = []
    for v in votes:
        user = User.query.get(v.user_id)
        voters.append({
            "username": user.username if user else "Unknown",
            "candidate": v.candidate,
            "photo": v.photo_path,
            "timestamp": v.timestamp
        })

    return render_template("admin_dashboard.html", count=count, voters=voters)

# ---------- Candidate Management ----------
@app.route("/candidates", methods=["GET", "POST"])
@login_required
def manage_candidates():
    if not current_user.is_admin:
        return redirect(url_for("vote_page"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            return jsonify({"error": "Name required"}), 400

        if Candidate.query.filter_by(name=name).first():
            return jsonify({"error": "Candidate already exists"}), 400

        candidate = Candidate(name=name)
        db.session.add(candidate)
        db.session.commit()
        return jsonify({"id": candidate.id, "name": candidate.name})

    candidates = Candidate.query.all()
    return render_template(
        "candidates.html",
        candidates=candidates,
        current_year=datetime.now().year
    )

@app.route("/edit_candidate/<int:candidate_id>", methods=["POST"])
@login_required
def edit_candidate(candidate_id):
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    candidate = Candidate.query.get_or_404(candidate_id)
    new_name = request.form.get("name", "").strip()

    if not new_name:
        return jsonify({"error": "Empty name"}), 400

    candidate.name = new_name
    db.session.commit()
    return jsonify({"success": True, "name": candidate.name})

@app.route("/delete_candidate/<int:candidate_id>", methods=["DELETE"])
@login_required
def delete_candidate(candidate_id):
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    candidate = Candidate.query.get_or_404(candidate_id)
    db.session.delete(candidate)
    db.session.commit()
    return jsonify({"success": True})

# -------------------- Run App --------------------
if __name__ == "__main__":
    app.run(debug=True)
