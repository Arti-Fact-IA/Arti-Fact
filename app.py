from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import pyodbc
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Configuration de la connexion SQL Server
app.config['SQLALCHEMY_DATABASE_URI'] = 'mssql+pyodbc://sa:1793@localhost/gestion_factures?driver=ODBC+Driver+17+for+SQL+Server'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'mon_super_secret'  # Change ce secret en prod !

db = SQLAlchemy(app)
jwt = JWTManager(app)

# Modèles SQLAlchemy
class Utilisateur(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    nom = db.Column(db.String(100), nullable=False)
    entreprise = db.Column(db.String(255), nullable=False)

# Création des tables
with app.app_context():
    db.create_all()

# ----------------------------- AUTHENTIFICATION -----------------------------

# 📌 Route d'inscription
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    hashed_password = generate_password_hash(data["password"])  # Hash du mot de passe

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

    # 🔥 Correction ici : Convertir l'ID en string
    access_token = create_access_token(identity=str(user.id))
    
    return jsonify({"access_token": access_token}), 200


# ----------------------------- ROUTES PROTÉGÉES -----------------------------

# 📌 Route protégée : Récupérer les factures de l'utilisateur connecté
@app.route("/factures", methods=["GET"])
@jwt_required()
def get_factures():
    user_id = get_jwt_identity()  # Récupérer l'utilisateur connecté
    factures = Facture.query.filter_by(user_id=user_id).all()

    factures_list = [
        {
            "id": f.id,
            "entreprise_emettrice": f.entreprise_emettrice,
            "nom_fichier": f.nom_fichier,
            "montant": float(f.montant),
            "date_facture": f.date_facture.strftime("%Y-%m-%d"),
            "status": f.status
        } for f in factures
    ]
    return jsonify(factures_list), 200

# ----------------------------- DÉMARRER FLASK -----------------------------

if __name__ == "__main__":
    app.run(debug=True)
