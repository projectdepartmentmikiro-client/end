from flask import Flask, request, jsonify, render_template, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
import json, os

# ===========================
# ⚙️ App Configuration
# ===========================
app = Flask(__name__)

# Database setup
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///website_results.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Session secret key (for login sessions)
app.secret_key = os.getenv("FLASK_SESSION_SECRET", "temporary_session_secret")

db = SQLAlchemy(app)

# ===========================
# 🔑 API and Login Secrets
# ===========================
UPLOAD_PUBLIC_KEY = os.getenv("UPLOAD_PUBLIC_KEY", "pk_42OXvyElpcR89RtMCMWzNlLH2dPYWAL_")
UPLOAD_SECRET_KEY = os.getenv("UPLOAD_SECRET_KEY", "sk_gjBya/FZDjrloBK4RbBBZ+BK4zUda9fU5MIrnzdFB8MUXbrIkM73vRzrnvwBH0hc")
LOGIN_SECRET_KEY = os.getenv("LOGIN_SECRET_KEY", "CDEWS-SECRET-2025")

# ===========================
# 🧩 Database Model
# ===========================
class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.String(100))
    device_code = db.Column(db.String(100))
    egg_count = db.Column(db.Integer)
    image_url = db.Column(db.String(300))
    binary_image_url = db.Column(db.String(300))
    annotated_image_url = db.Column(db.String(300))
    bounding_boxes = db.Column(db.Text)

# ===========================
# 🧱 Initialize Database
# ===========================
with app.app_context():
    db.create_all()
    print("✅ Database tables created or verified.")

# ===========================
# 🔐 Login System
# ===========================
@app.route("/", methods=["GET", "POST"])
def login():
    """Handles login via secret key."""
    if session.get("authenticated"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        entered_key = request.form.get("secret_key")
        if entered_key == LOGIN_SECRET_KEY:
            session["authenticated"] = True
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="Invalid secret key")

    return render_template("login.html")


@app.route("/logout")
def logout():
    """Clears session and redirects to login."""
    session.pop("authenticated", None)
    return redirect(url_for("login"))


# ===========================
# 📊 Dashboard
# ===========================
@app.route("/dashboard")
def dashboard():
    """Main dashboard displaying uploaded egg detection results."""
    if not session.get("authenticated"):
        return redirect(url_for("login"))

    results = Result.query.order_by(Result.id.desc()).all()
    return render_template("dashboard.html", results=results)


# ===========================
# 🛰️ API Endpoints
# ===========================
@app.route("/api/upload_results", methods=["POST"])
def upload_results():
    """Receives result data from IoT or Pi device."""
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON payload"}), 400

    client_pk = data.get("api_key")
    client_sk = data.get("api_secret")

    # Validate API keys
    if client_pk != UPLOAD_PUBLIC_KEY or client_sk != UPLOAD_SECRET_KEY:
        return jsonify({"error": "Unauthorized - invalid keys"}), 401

    # Create a new record in database
    try:
        new_result = Result(
            timestamp=data.get("timestamp"),
            device_code=data.get("device_code"),
            egg_count=int(data.get("egg_count", 0)),
            image_url=data.get("image_url"),
            binary_image_url=data.get("binary_image_url"),
            annotated_image_url=data.get("annotated_image_url"),
            bounding_boxes=json.dumps(data.get("bounding_boxes", [])),
        )
        db.session.add(new_result)
        db.session.commit()
        return jsonify({"message": "Data saved successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Database error: {str(e)}"}), 500


@app.route("/api/results", methods=["GET"])
def get_results():
    """Fetch all results (secured by API keys)."""
    client_pk = request.headers.get("X-API-Key")
    client_sk = request.headers.get("X-API-Secret")

    if client_pk != UPLOAD_PUBLIC_KEY or client_sk != UPLOAD_SECRET_KEY:
        return jsonify({"error": "Unauthorized"}), 401

    results = Result.query.order_by(Result.id.desc()).all()
    return jsonify([
        {
            "timestamp": r.timestamp,
            "device_code": r.device_code,
            "egg_count": r.egg_count,
            "image_url": r.image_url,
            "binary_image_url": r.binary_image_url,
            "annotated_image_url": r.annotated_image_url,
        }
        for r in results
    ])


# ===========================
# 🩺 Health Check
# ===========================
@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


# ===========================
# ⚠️ Error Handling
# ===========================
@app.errorhandler(404)
def not_found(e):
    return redirect(url_for("login"))


# ===========================
# 🚀 App Runner
# ===========================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        print("✅ Local database ready.")
    app.run(host="0.0.0.0", port=5000)
