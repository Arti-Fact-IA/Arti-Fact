from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import pytesseract
from pdf2image import convert_from_path
from PIL import Image

# Configuration Flask
app = Flask(__name__)

# Configuration de la connexion PostgreSQL sur Render
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "postgresql://gestion_factures_db_user:Oma1Km2GDdOjrcDLif9dUStXDpdnqfWN@dpg-cuqk8a5ds78s73fuolg0-a.frankfurt-postgres.render.com/gestion_factures_db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'mon_super_secret'

db = SQLAlchemy(app)
jwt = JWTManager(app)

# Initialisation de la base de données et JWT
db = SQLAlchemy(app)
jwt = JWTManager(app)

# 📂 Dossier de stockage des factures
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Vérifie si le fichier est une facture valide (PDF/Image)
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ----------------------------- MODÈLES -----------------------------

class Utilisateur(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    nom = db.Column(db.String(100), nullable=False)
    entreprise = db.Column(db.String(255), nullable=False)

class Facture(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('utilisateur.id'), nullable=False)
    entreprise_emettrice = db.Column(db.String(255), nullable=False)
    nom_fichier = db.Column(db.String(255), nullable=False)
    montant = db.Column(db.Numeric(10,2), nullable=True)
    date_facture = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(50), default='en attente')

# Création des tables en base
with app.app_context():
    db.create_all()

# ----------------------------- ROUTES AUTHENTIFICATION -----------------------------

# 📌 Route d'inscription
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    hashed_password = generate_password_hash(data["password"])
    
    new_user = Utilisateur(
        email=data["email"],
        password_hash=hashed_password,
        nom=data["nom"],
        entreprise=data["entreprise"]
    )
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "Utilisateur enregistré avec succès"}), 201

# 📌 Route de connexion
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    user = Utilisateur.query.filter_by(email=data["email"]).first()

    if not user or not check_password_hash(user.password_hash, data["password"]):
        return jsonify({"message": "Identifiants incorrects"}), 401

    access_token = create_access_token(identity=str(user.id))
    return jsonify({"access_token": access_token}), 200

# ----------------------------- ROUTES FACTURES -----------------------------

# 📌 Route pour téléverser une facture
@app.route("/upload", methods=["POST"])
@jwt_required()
def upload_file():
    if "file" not in request.files:
        return jsonify({"message": "Aucun fichier reçu"}), 400
    
    file = request.files["file"]

    if file.filename == "":
        return jsonify({"message": "Nom de fichier invalide"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        # 🔥 Extraction du texte via OCR
        extracted_text = extract_text(filepath)

        # 📌 Enregistrement en base de données
        new_facture = Facture(
            user_id=get_jwt_identity(),
            entreprise_emettrice="Inconnue",  # Remplacé après OCR
            nom_fichier=filename,
            montant=None,  # À extraire de l'OCR
            date_facture=None,  # À extraire de l'OCR
            status="en attente"
        )
        db.session.add(new_facture)
        db.session.commit()

        return jsonify({
            "message": "Fichier téléversé avec succès",
            "facture_id": new_facture.id,
            "contenu_extrait": extracted_text
        }), 201

    return jsonify({"message": "Format de fichier non supporté"}), 400

# 📌 Route pour récupérer toutes les factures d’un utilisateur
@app.route("/factures", methods=["GET"])
@jwt_required()
def get_factures():
    user_id = get_jwt_identity()
    factures = Facture.query.filter_by(user_id=user_id).all()

    factures_list = [
        {
            "id": f.id,
            "entreprise_emettrice": f.entreprise_emettrice,
            "nom_fichier": f.nom_fichier,
            "montant": float(f.montant) if f.montant else None,
            "date_facture": f.date_facture.strftime("%Y-%m-%d") if f.date_facture else None,
            "status": f.status
        } for f in factures
    ]
    return jsonify(factures_list), 200

# ----------------------------- OCR : EXTRACTION DE TEXTE -----------------------------

def extract_text(filepath):
    if filepath.lower().endswith(".pdf"):
        images = convert_from_path(filepath)
        text = ""
        for img in images:
            text += pytesseract.image_to_string(img)
        return text
    elif filepath.lower().endswith((".png", ".jpg", ".jpeg")):
        img = Image.open(filepath)
        return pytesseract.image_to_string(img)
    return "Format non supporté"

# ----------------------------- ROUTE D'ACCUEIL -----------------------------

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "API Gestion Factures OK"}), 200

# ----------------------------- DÉMARRER FLASK -----------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  
    app.run(host="0.0.0.0", port=port, debug=True)