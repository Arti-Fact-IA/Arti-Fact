# 🔹 Utilisation d'une image Python légère
FROM python:3.11-slim

# 🔹 Définition du dossier de travail
WORKDIR /app

# Copier les fichiers nécessaires
COPY requirements.txt .

# 🔹 Installation des dépendances
RUN pip install --no-cache-dir -r requirements.txt

# 🔹 Copie des fichiers du projet
COPY . .

# 🔹 Exposition du port Flask (5000)
EXPOSE 5000

# 🔹 Démarrage de l'application
CMD ["python", "app.py"]
