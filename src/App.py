import os

import numpy as np
from bson import ObjectId
from flask import Flask, request, jsonify
from pymongo import MongoClient
import gridfs
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity

import datetime

from modules.utils import *
from modules.processor import PreClustering, IndoorPositioning

import logging

logging.basicConfig(level=logging.ERROR, format='%(asctime)s %(levelname)s: %(message)s')

app = Flask(__name__)

db_url = os.getenv("DATABASE_URL")
db_name = os.getenv("DATABASE")

# Connessione a MongoDB
client = MongoClient(db_url)
db = client[db_name]
models_coll = db['models']
fs = gridfs.GridFS(db)
model_manager = ModelsManager(fs)

app.config['JWT_SECRET_KEY'] = os.getenv("JWT_SECRET")
jwt = JWTManager(app)

users = {
    os.getenv("USERNAME"): os.getenv("PASSWORD")
}


# User Login to generate JWT Token
@app.route('/login', methods=['POST'])
def login():
    if not request.is_json:
        return jsonify({"msg": "Missing JSON in request"}), 400

    username = request.json.get('username', None)
    password = request.json.get('password', None)

    # Check if user exists and password is correct
    if username not in users or users[username] != password:
        return jsonify({"msg": "Bad username or password"}), 401

    # Create access token
    access_token = create_access_token(identity=username, expires_delta=datetime.timedelta(minutes=15))
    return jsonify(access_token=access_token), 200


@app.route('/models/upload', methods=['POST'])
@jwt_required()
def upload_file():
    try:
        # Check if a file is part of the request
        if 'file' not in request.files:
            return jsonify({"error": "No file part in the request"}), 400

        file = request.files['file']
        name = request.form.get('name')
        description = request.form.get('description')
        timestamp = request.form.get('timestamp')

        if not (name and description and timestamp):
            return jsonify({"error": "Missing required metadata (name, description, timestamp)"}), 400

        # Convert the timestamp to a datetime object
        # Convert isoformat string to datetime object
        try:
            timestamp = datetime.datetime.fromisoformat(timestamp)
        except ValueError:
            return jsonify({"error": "Invalid timestamp format. Use 'YYYY-MM-DDTHH:MM:SS'"}), 400

        # Store the file in GridFS along with metadata
        file_id = fs.put(file, filename=name, metadata={'description': description, 'timestamp': timestamp})

        return jsonify({
            "message": "File uploaded successfully",
            "file_id": str(file_id),
            "filename": name,
            "description": description,
            "timestamp": timestamp.isoformat()
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/models/<file_id>', methods=['GET'])
@jwt_required()
def get_file(file_id):
    try:
        # Fetch the file from GridFS
        file = fs.get(ObjectId(file_id))

        return jsonify({
            "filename": file.filename,
            "size_mb": file.length * 1e-6,  # Convert bytes to MB
            "description": file.metadata.get('description'),
            "timestamp": file.metadata.get('timestamp').isoformat()
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/models/download/<file_id>', methods=['GET'])
@jwt_required()
def download_file(file_id):
    try:
        # Fetch the file from GridFS
        file = fs.get(ObjectId(file_id))

        # Set the response headers to send the file to the client
        response = app.response_class(
            file,
            mimetype='application/octet-stream',
            headers={"Content-Disposition": f"attachment; filename={file.filename}"}
        )

        return response

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/models', methods=['GET'])
@jwt_required()
def get_all_files():
    # Restituisce tutti gli id e i nomi dei file
    files = []
    for file in fs.find():
        files.append({
            "file_id": str(file._id),
            "filename": file.filename,
            "size_mb": file.length * 1e-6,
            "description": file.metadata.get('description'),
            "timestamp": file.metadata.get('timestamp').isoformat()
        })

    return jsonify(files), 200


@app.route('/models/delete/<file_id>', methods=['DELETE'])
@jwt_required()
def delete_file(file_id):
    try:
        # Delete the file from GridFS
        fs.delete(ObjectId(file_id))
        return jsonify({"message": "File deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/models/latest', methods=['GET'])
@jwt_required()
def get_latest_models():
    try:
        # Ottieni il modello KMeans più recente e i modelli KNN associati
        kmeans_model, knn_models = model_manager.get_all_models()

        # Preparare la risposta JSON (qui puoi includere dettagli sul KMeans e i KNN)
        response = {
            "kmeans_model": {kmeans_model.filename: kmeans_model.metadata['timestamp']},
            # Stampa il modello KMeans in modo leggibile
            "knn_models": {filename: str(knn.metadata['timestamp']) for filename, knn in knn_models.items()}
            # Modelli KNN senza duplicati
        }

        return jsonify(response), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/position', methods=['GET'])
def get_position():
    try:
        if not request.is_json:
            return jsonify({"msg": "Missing JSON in request"}), 400

        data = request.json
        if 'rssi' not in data:
            return jsonify({"error": "Missing 'rssi' key in request"}), 400

        rssi = np.array(data['rssi'])
        kmeans_model, knn_models = model_manager.get_all_models()

        # Carica il modello KMeans
        kmeans_model = load_kmeans_model(kmeans_model)
        if kmeans_model is None:
            return jsonify({"error": "Service not available"}), 404

        kmeans_result = kmeans_model.mle_predict(rssi, results=True)
        # Check if returned value is a list
        if isinstance(kmeans_result, tuple):
            kmeans_result = kmeans_result[0]

        knn_model = None
        # Carica il modello KNN associato al cluster estraendo il file col nome che termina col numero del cluster
        for knn in knn_models.values():
            if knn.filename.endswith(str(kmeans_result)):
                knn_model = knn
                break

        if knn_model is None:
            return jsonify({"error": "No available service. Missing configuration"}), 404

        knn_model = load_knn_model(knn_model)

        if knn_model is None:
            return jsonify({"error": "Service not available"}), 404

        position = knn_model.predict(rssi, clean=False)
        position = knn_model.get_position(position)

        return jsonify({"position":
                            {
                                "x": position['x'],
                                "y": position['y'],
                                'RP': position.name
                            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
