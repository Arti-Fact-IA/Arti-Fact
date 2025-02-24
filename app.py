from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import requests
from pdf2image import convert_from_path
from PIL import Image
from flask_cors import CORS

# Configuration Flask
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "https://arti-fact-frontend.onrender.com"}})


# Configuration de la base PostgreSQL sur Render
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'mon_super_secret'

# Initialisation de la base de données et JWT
db = SQLAlchemy()
jwt = JWTManager(app)
db.init_app(app)

# 📂 Dossier de stockage des factures
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ✅ Vérifier et créer le dossier "uploads" s'il n'existe pas
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# 🔑 Clé API OCR.space (à récupérer sur https://ocr.space/OCRAPI)
OCR_API_KEY = "K86754708488957"  # Remplace par ta clé API OCR.space

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
    entreprise_emettrice = db.Column(db.String(255), nullable=False, default="NC")
    nom_fichier = db.Column(db.String(255), nullable=False)
    montant = db.Column(db.Numeric(10,2), nullable=True)
    date_facture = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(50), default='en attente')

# Création des tables après l'initialisation de l'app
with app.app_context():
    db.create_all()

# ----------------------------- ROUTES AUTHENTIFICATION -----------------------------

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

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    user = Utilisateur.query.filter_by(email=data["email"]).first()

    if not user or not check_password_hash(user.password_hash, data["password"]):
        return jsonify({"message": "Identifiants incorrects"}), 401

    access_token = create_access_token(identity=str(user.id))
    return jsonify({"access_token": access_token}), 200

# ----------------------------- ROUTES FACTURES -----------------------------

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

        extracted_text = extract_text(filepath)

        # 🚀 Vérification et valeurs par défaut
        entreprise_emettrice = "NC"  # Par défaut si non trouvée
        montant = None  # Peut être NULL
        date_facture = None  # Peut être NULL

        new_facture = Facture(
            user_id=get_jwt_identity(),
            entreprise_emettrice=entreprise_emettrice,
            nom_fichier=filename,
            montant=montant,
            date_facture=date_facture,
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

@app.route("/factures/<int:facture_id>/articles", methods=["GET"])
@jwt_required()
def get_articles(facture_id):
    user_id = get_jwt_identity()
    facture = Facture.query.filter_by(id=facture_id, user_id=user_id).first()

    if not facture:
        return jsonify({"message": "Facture introuvable"}), 404

    articles = Article.query.filter_by(facture_id=facture.id).all()
    articles_list = [{"nom": a.nom, "quantite": a.quantite, "prix": float(a.prix)} for a in articles]

    return jsonify(articles_list), 200


# ----------------------------- OCR -----------------------------

def extract_text(filepath):
    with open(filepath, "rb") as file:
        response = requests.post(
            "https://api.ocr.space/parse/image",
            files={"file": file},
            data={"apikey": OCR_API_KEY, "language": "fre"},
        )

    result = response.json()
    
    if result["IsErroredOnProcessing"]:
        return "Erreur OCR : " + result["ErrorMessage"][0]

    extracted_text = result["ParsedResults"][0]["ParsedText"]
    return extracted_text.strip()

# ----------------------------- ROUTE D'ACCUEIL -----------------------------

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "API Gestion Factures OK"}), 200

# ----------------------------- DÉMARRER FLASK -----------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  
    app.run(host="0.0.0.0", port=port, debug=True)
