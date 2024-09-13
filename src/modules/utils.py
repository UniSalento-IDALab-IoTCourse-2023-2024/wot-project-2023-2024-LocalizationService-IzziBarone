import enum
from io import BytesIO

from gridfs import GridFS
from modules.processor import PreClustering, IndoorPositioning


def load_kmeans_model(model_file) -> PreClustering | None:
    try:
        model_obj = PreClustering(None)
        model_file.seek(0)
        model_data = model_file.read()
        model_obj.load_model(BytesIO(model_data))
        return model_obj
    except Exception as e:
        raise None


def load_knn_model(model_file) -> IndoorPositioning | None:
    try:
        model_obj = IndoorPositioning(None)
        model_file.seek(0)
        model_data = model_file.read()
        model_obj.load_model(BytesIO(model_data))
        return model_obj
    except Exception as e:
        raise None


class ModelsManager:
    __MODELS_CATEGORY__ = {"knn": 'KNN', "kmeans": 'KMeans'}

    def __init__(self, fs: GridFS):
        self.fs = fs

    def get_latest_model(self, category):
        """Recupera il modello KMeans più recente in base alla categoria e al timestamp."""
        latest_kmeans_file = self.fs.find_one(
            {'metadata.description': category},  # Filtra per la categoria
            sort=[('metadata.timestamp', -1)]  # Ordina per timestamp decrescente
        )

        if not latest_kmeans_file:
            raise ValueError(f"No KMeans model found for category '{category}'")

        return latest_kmeans_file, latest_kmeans_file.metadata['timestamp']

    def get_latest_models_by_date(self, category, kmeans_timestamp, n_clusters):
        """Recupera i modelli KNN più recenti per ciascun cluster associato al KMeans, cercando per categoria."""
        knn_models = {}
        knn_files = self.fs.find({
            'metadata.description': category,
            'metadata.timestamp': {'$gte': kmeans_timestamp}  # Cerca file prima o uguali al timestamp del KMeans
        }).sort('metadata.timestamp', -1)  # Ordina per timestamp decrescente

        # Check also for knn_files with timestamp greater than kmeans_timestamp
        count = list(knn_files)
        knn_files.rewind()
        if len(count) < n_clusters:
            # Search for all knn_files
            knn_files = self.fs.find({
                'metadata.description': category,
            }).sort('metadata.timestamp', -1)

        # Raggruppa i modelli KNN per filename
        for knn_file in knn_files:
            filename = knn_file.filename
            if filename not in knn_models:
                # Se il modello KNN con questo nome non è stato ancora aggiunto, prendi il più recente
                knn_models[filename] = knn_file
            else:
                # Se modello già presente, confrontare le date e tenere il più recente
                existing_timestamp = knn_models[filename].metadata['timestamp']
                if knn_file.metadata['timestamp'] > existing_timestamp:
                    knn_models[filename] = knn_file

        # Controlla se ci sono modelli KNN per tutti i cluster
        if len(knn_models) != n_clusters:
            raise ValueError(f"Missing KNN models for all clusters in category '{category}'")

        return knn_models

    def get_all_models(self):
        """Recupera il modello KMeans più recente e i modelli KNN associati."""
        kmeans_model, kmeans_timestamp = self.get_latest_model(self.__MODELS_CATEGORY__['kmeans'])
        model_obj = PreClustering(None)

        model_data = kmeans_model.read()
        try:
            model_obj.load_model(BytesIO(model_data))
        except Exception as e:
            raise ValueError(f"Error loading model: {e}")

        n_clusters = model_obj.get_clusters(data=False)
        knn_models = self.get_latest_models_by_date(self.__MODELS_CATEGORY__['knn'], kmeans_timestamp, n_clusters)
        return kmeans_model, knn_models
