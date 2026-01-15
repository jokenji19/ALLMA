from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import timedelta
import os
import sys

# Aggiungi il path per importare i moduli ALLMA
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from allma_model.core.allma_core import AllmaCore
from allma_model.project_system.project_tracker import ProjectTracker
from allma_model.emotional_system.emotional_core import EmotionalCore

app = Flask(__name__)
CORS(app)

# Configurazione JWT
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'your-secret-key')  # Cambia in produzione
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
jwt = JWTManager(app)

# Inizializza i componenti ALLMA
allma = AllmaCore()
project_tracker = ProjectTracker()
emotional_core = EmotionalCore()

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Endpoint per il login"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    # TODO: Implementa la vera autenticazione
    if username == "admin" and password == "password":
        access_token = create_access_token(identity=username)
        return jsonify(access_token=access_token), 200
    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/api/projects', methods=['GET'])
@jwt_required()
def get_projects():
    """Ottieni tutti i progetti"""
    current_user = get_jwt_identity()
    projects = project_tracker.get_all_projects(current_user)
    return jsonify(projects), 200

@app.route('/api/projects', methods=['POST'])
@jwt_required()
def create_project():
    """Crea un nuovo progetto"""
    current_user = get_jwt_identity()
    data = request.get_json()
    
    project_id = project_tracker.create_project(
        current_user,
        data['name'],
        data['description'],
        data.get('metadata', {})
    )
    return jsonify({"project_id": project_id}), 201

@app.route('/api/projects/<project_id>', methods=['GET'])
@jwt_required()
def get_project(project_id):
    """Ottieni dettagli di un progetto specifico"""
    project = project_tracker.get_project_summary(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404
    return jsonify(project), 200

@app.route('/api/emotional/state', methods=['GET'])
@jwt_required()
def get_emotional_state():
    """Ottieni lo stato emotivo corrente"""
    current_user = get_jwt_identity()
    state = emotional_core.get_current_state()
    return jsonify(state), 200

@app.route('/api/conversation', methods=['POST'])
@jwt_required()
def send_message():
    """Invia un messaggio ad ALLMA"""
    current_user = get_jwt_identity()
    data = request.get_json()
    message = data['message']
    
    # Processa il messaggio con ALLMA
    response = allma.process_message(message, {"user_id": current_user})
    return jsonify({"response": response}), 200

@app.route('/api/learning/progress', methods=['GET'])
@jwt_required()
def get_learning_progress():
    """Ottieni il progresso dell'apprendimento"""
    current_user = get_jwt_identity()
    progress = allma.get_learning_progress(current_user)
    return jsonify(progress), 200

@app.route('/api/dashboard/stats', methods=['GET'])
@jwt_required()
def get_dashboard_stats():
    """Ottieni le statistiche per la dashboard"""
    current_user = get_jwt_identity()
    
    stats = {
        "projects": project_tracker.get_project_stats(current_user),
        "emotional": emotional_core.get_emotional_stats(),
        "learning": allma.get_learning_stats(current_user),
        "conversation": allma.get_conversation_stats(current_user)
    }
    return jsonify(stats), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)
