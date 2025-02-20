import random  # ✅ Ajout du module pour générer un email unique
import requests


# URL de l'API (modifie si nécessaire)
BASE_URL = "https://arti-fact-7tix.onrender.com/" 

TOKEN = None  
TEST_EMAIL = f"testuser_{random.randint(1000, 9999)}@example.com" #en mode random user

# 🔑 Vérifie si l'utilisateur existe avant de le créer
def test_register():
    url = f"{BASE_URL}/register"
    data = {
        "email": TEST_EMAIL,
        "password": "password123",
        "nom": "Test User",
        "entreprise": "Test Entreprise"
    }
    response = requests.post(url, json=data)
    
    if response.status_code == 409:
        print("ℹ️ L'utilisateur existe déjà.")
    else:
        assert response.status_code in [200, 201], f"Erreur: {response.text}"

# 🔑 Connexion et récupération du token JWT
def test_login():
    global TOKEN  
    url = f"{BASE_URL}/login"
    data = {
        "email": TEST_EMAIL,
        "password": "password123"
    }
    response = requests.post(url, json=data)
    
    assert response.status_code == 200, f"Erreur: {response.text}"
    
    TOKEN = response.json().get("access_token")
    assert TOKEN, "Token non reçu"

# 📂 Test de l'upload d'un fichier valide
def test_upload():
    test_login()  
    url = f"{BASE_URL}/upload"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    files = {"file": open("facture_test.png", "rb")}  
    response = requests.post(url, headers=headers, files=files)
    assert response.status_code in [200, 201], f"Erreur: {response.text}"

# 📋 Test de récupération des factures
def test_get_factures():
    url = f"{BASE_URL}/factures"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    response = requests.get(url, headers=headers)
    
    assert response.status_code == 200, f"Erreur: {response.text}"
    factures = response.json()
    assert isinstance(factures, list), "La réponse doit être une liste"

# ❌ Test upload sans authentification
def test_upload_unauthorized():
    url = f"{BASE_URL}/upload"
    files = {"file": open("facture_test.png", "rb")}
    response = requests.post(url, files=files)  # Pas d'Authorization header
    assert response.status_code == 401, f"Erreur: {response.text}"

# ❌ Test upload avec un fichier invalide
def test_upload_invalid_file():
    test_login()
    url = f"{BASE_URL}/upload"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    files = {"file": open("invalid_file.txt", "rb")}
    response = requests.post(url, headers=headers, files=files)
    assert response.status_code == 400, f"Erreur: {response.text}"

# ❌ Test login avec un mauvais mot de passe
def test_login_invalid_password():
    url = f"{BASE_URL}/login"
    data = {
        "email": TEST_EMAIL,
        "password": "wrongpassword"
    }
    response = requests.post(url, json=data)
    assert response.status_code == 401, f"Erreur: {response.text}"

# ❌ Test récupération des factures sans token
def test_get_factures_unauthorized():
    url = f"{BASE_URL}/factures"
    response = requests.get(url)  # Pas d'Authorization header
    assert response.status_code == 401, f"Erreur: {response.text}"

if __name__ == "__main__":
    test_register()
    test_login()
    test_upload()
    test_get_factures()
    test_upload_unauthorized()
    test_upload_invalid_file()
    test_login_invalid_password()
    test_get_factures_unauthorized()
    print("✅ Tous les tests sont passés avec succès !")