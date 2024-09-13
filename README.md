# SmartLocAI - LocalizationService API

## Overview

Il **LocalizationService API** è un servizio backend sviluppato in **Flask** che gestisce il deployment, la gestione e il recupero dei modelli di machine learning, come **K-Means** e **KNN**, utilizzati per la localizzazione indoor. Questo servizio consente di caricare, scaricare e versionare i modelli, oltre a fornire funzionalità per calcolare in tempo reale la posizione di un dispositivo basandosi sui dati **RSSI** inviati.

## a) Architettura del Sistema

Il **LocalizationService API** è parte integrante dell'architettura di **SmartLocAI** e gestisce il deployment e l'esecuzione dei modelli utilizzati per la localizzazione. I principali componenti che interagiscono con questo servizio includono:

- **App Mobile SmartLocAI**: Raccoglie i dati RSSI dai dispositivi mobili e richiede la posizione stimata.
- **DataService API**: Fornisce i dati preprocessati per l'addestramento dei modelli.
- **LocalizationService API**: Gestisce i modelli di machine learning e calcola la posizione del dispositivo in tempo reale.
- **MongoDB con GridFS**: Archivia i modelli di machine learning e ne gestisce le versioni.

### Flusso di lavoro:
1. **Login e autenticazione JWT**: Gli utenti si autenticano per ottenere un token JWT necessario per accedere ai servizi protetti.
2. **Upload dei modelli**: Caricamento dei modelli K-Means e KNN utilizzati per la localizzazione.
3. **Download e gestione dei modelli**: Recupero e gestione dei modelli per eseguire la localizzazione.
4. **Calcolo della posizione**: Predizione della posizione del dispositivo in base ai dati RSSI forniti dall'app mobile.

## b) Repositori dei Componenti

- **LocalizationService API**: [Link al repository](https://github.com/UniSalento-IDALab-IoTCourse-2023-2024/wot-project-2023-2024-LocalizationService-IzziBarone)
- **DataService API**: [Link al repository](https://github.com/UniSalento-IDALab-IoTCourse-2023-2024/wot-project-2023-2024-DataService-IzziBarone.git)
- **Preprocessing Dashboard**: [Link al repository](https://github.com/UniSalento-IDALab-IoTCourse-2023-2024/wot-project-2023-2024-Dashboard-IzziBarone.git)

## c) Endpoint Principali del LocalizationService API

### 1. Autenticazione

- **POST /login**: Autentica l'utente e restituisce un token JWT.
   - Esempio di request:
     ```json
     {
       "username": "admin",
       "password": "password123"
     }
     ```
   - Risposta: `200 OK` con il token JWT.

### 2. Gestione dei Modelli

- **POST /models/upload**: Carica un nuovo modello di machine learning (K-Means o KNN) in GridFS.
   - Esempio di request:
     - Metadata: nome del file, descrizione, timestamp (ISO 8601).
     - File: Modello di machine learning.
     - Esempio di form-data:
       ```
       name: "kmeans_model"
       description: "K-Means model for clustering"
       timestamp: "2024-01-01T10:00:00"
       file: [file]
       ```
   - Risposta: `201 Created` con l'ID del file caricato.

- **GET /models/<file_id>**: Restituisce i dettagli di un modello specifico in base all'ID.
   - Esempio di request: `GET /models/60b9e7b2f1e1463d7b3d492b`
   - Risposta: Dettagli del modello, inclusi nome, descrizione, dimensione e timestamp.

- **GET /models/download/<file_id>**: Scarica un modello specifico in base all'ID.
   - Esempio di request: `GET /models/download/60b9e7b2f1e1463d7b3d492b`
   - Risposta: File del modello.

- **DELETE /models/delete/<file_id>**: Elimina un modello specifico in base all'ID.
   - Esempio di request: `DELETE /models/delete/60b9e7b2f1e1463d7b3d492b`
   - Risposta: `200 OK` se il file è stato eliminato.

- **GET /models/latest**: Restituisce il modello K-Means più recente e i modelli KNN associati.
   - Risposta: Dettagli del modello K-Means e dei modelli KNN.

### 3. Calcolo della Posizione

- **GET /position**: Calcola la posizione del dispositivo basandosi sui dati RSSI forniti.
   - Esempio di request:
     ```json
     {
       "rssi": [70, 65, 80]
     }
     ```
   - Risposta: `200 OK` con la posizione stimata.
     ```json
     {
       "position": {
         "x": 1,
         "y": 1,
         "RP": "..."
       }
     }
     ```

### 4. Visualizzazione di tutti i modelli

- **GET /models**: Restituisce una lista di tutti i modelli memorizzati in GridFS.
   - Risposta: `200 OK` con una lista di modelli (ID, nome, dimensione, timestamp).

---

### Come Iniziare

1. Clona il repository:
   ```bash
   git clone https://github.com/UniSalento-IDALab-IoTCourse-2023-2024/wot-project-2023-2024-LocalizationService-IzziBarone.git
   ```
2. Environment:
   ```python
   DATABASE_URL=mongodb://dbloc:27017/database
   DATABASE=database
   PASSWORD=*****
   USERNAME=****
   JWT_SECRET=****** [Same as DataServiceAPI]
   ```
2. Docker compose:
   ```bash
   docker compose up -d
   ```
### Autenticazione

Tutti gli endpoint che gestiscono modelli e calcolano la posizione richiedono l'autenticazione tramite **JWT** (JSON Web Token). Per ottenere un token JWT, è necessario autenticarsi tramite l'endpoint di login, e includere il token nelle intestazioni di tutte le richieste protette.
