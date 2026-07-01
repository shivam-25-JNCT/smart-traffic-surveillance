# 🚦 Smart Traffic Surveillance System (Phase 1)

## 📌 Project Overview

This project is a production-oriented AI-based **Smart Traffic Surveillance System**.

The system captures live video from an RTSP camera, detects vehicles, identifies their number plates, extracts plate text using OCR, and stores all detections in a PostgreSQL database.

The project follows a modular architecture with separate **Frontend**, **Backend**, and **Database** layers, making it scalable, maintainable, and easy to extend with future traffic monitoring features.

---

# 🎯 Phase 1 Goals

The first phase focuses on **Automatic Number Plate Recognition (ANPR)**.

### Features

- Connect to RTSP Camera
- Read Live Video Stream
- Detect Vehicles (Car, Bike, Bus, Truck)
- Detect Number Plates
- Crop Number Plate Images
- Extract Plate Text using PaddleOCR
- Store Detection Records in PostgreSQL
- Save Detection Timestamp
- Save Camera Information
- Save Cropped Plate Images
- Display Live Camera Feed in Streamlit
- View Detection History
- Search Vehicle by Plate Number

---

# 🏗 System Architecture

```text
                  Streamlit Frontend
                         │
                  REST API Request
                         │
                         ▼
                  FastAPI Backend
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
   RTSP Camera      YOLO Detection    PostgreSQL
        │                │
        ▼                ▼
     OpenCV         PaddleOCR
```

---

# 📂 Project Structure

```text
traffic-anpr/

│
├── backend/
│   │
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   │
│   │   ├── api/
│   │   │     └── routes.py
│   │   │
│   │   ├── camera/
│   │   │     └── rtsp.py
│   │   │
│   │   ├── detector/
│   │   │     ├── vehicle.py
│   │   │     └── plate.py
│   │   │
│   │   ├── ocr/
│   │   │     └── paddle.py
│   │   │
│   │   ├── database/
│   │   │     ├── db.py
│   │   │     ├── models.py
│   │   │     └── crud.py
│   │   │
│   │   ├── services/
│   │   │     └── anpr_service.py
│   │   │
│   │   └── utils/
│   │         ├── image.py
│   │         └── logger.py
│   │
│   ├── weights/
│   ├── evidence/
│   ├── requirements.txt
│   └── .env
│
├── frontend/
│   │
│   ├── app.py
│   ├── api.py
│   ├── pages/
│   │     ├── dashboard.py
│   │     ├── live_camera.py
│   │     ├── detections.py
│   │     └── search.py
│   │
│   ├── assets/
│   └── requirements.txt
│
├── README.md
├── requirements.txt
└── .gitignore
```

---

# 📖 Folder Responsibilities

## Backend

The backend contains the complete AI pipeline and database operations.

### `main.py`

- FastAPI application entry point
- Starts the backend server
- Registers API routes

---

### `config.py`

Stores project configuration.

Examples:

- RTSP URL
- PostgreSQL credentials
- Model paths
- Confidence thresholds

No business logic should be written here.

---

### `api/routes.py`

Contains FastAPI endpoints.

Examples:

- Start Camera
- Stop Camera
- Camera Status
- Detection History
- Search Plate
- Live Stream

Routes should only handle requests and responses.

---

### `camera/`

Responsible for camera communication.

Tasks:

- Connect RTSP stream
- Read frames
- Handle reconnection
- Release camera

---

### `detector/`

Contains AI detection modules.

#### `vehicle.py`

Detects:

- Car
- Bike
- Bus
- Truck

Returns vehicle bounding boxes.

#### `plate.py`

Detects number plates.

Returns plate bounding boxes.

---

### `ocr/`

Uses PaddleOCR.

Responsibilities:

- Read cropped plate image
- Clean OCR output
- Validate plate format
- Return final plate number

---

### `database/`

Contains database-related modules.

#### `db.py`

Creates PostgreSQL connection.

Initializes SQLAlchemy engine and session.

#### `models.py`

Defines SQLAlchemy models.

Examples:

- Cameras
- Detections

#### `crud.py`

Contains all database operations.

Examples:

- Insert Detection
- Get Detection
- Search Detection
- Update Detection

No SQL queries should be written outside this module.

---

### `services/`

Contains business logic.

Current:

- ANPR Pipeline

Future:

- Vehicle Tracking
- Duplicate Plate Detection
- Alert Service
- Evidence Service

---

### `utils/`

Reusable helper functions.

Examples:

- Image processing
- Logging
- Timestamp formatting

---

### `weights/`

Stores AI model weights.

Examples:

- Vehicle Detection Model
- Number Plate Detection Model

---

### `evidence/`

Stores cropped plate images.

Future versions may also store:

- Full frame images
- Video clips
- Evidence packages

---

# Frontend

The frontend is built using **Streamlit**.

Responsibilities:

- Display Live Camera Feed
- Display Detection History
- Search Number Plate
- Show Camera Status
- Display Statistics

The frontend communicates only with the FastAPI backend through REST APIs.

---

# 🗄 Database Design

## cameras

| Column | Description |
|----------|-------------|
| id | Camera ID |
| camera_name | Camera Name |
| rtsp_url | RTSP Stream URL |
| latitude | Camera Latitude |
| longitude | Camera Longitude |

---

## detections

| Column | Description |
|----------|-------------|
| id | Detection ID |
| camera_id | Camera Reference |
| vehicle_type | Vehicle Type |
| plate_number | OCR Result |
| confidence | OCR Confidence |
| image_path | Cropped Plate Image |
| timestamp | Detection Time |

---

# 🛠 Technology Stack

| Technology | Purpose |
|------------|---------|
| Python | Core Language |
| Streamlit | Frontend |
| FastAPI | Backend API |
| OpenCV | RTSP Video Processing |
| YOLO | Vehicle & Plate Detection |
| PaddleOCR | Number Plate Recognition |
| PostgreSQL | Database |
| SQLAlchemy | ORM |
| Git | Version Control |

---

# 🚀 Future Roadmap

## Phase 2

- Vehicle Tracking (ByteTrack)
- Duplicate Plate Filtering

## Phase 3

- Analytics Dashboard
- Multiple Camera Support
- Live Monitoring
- Advanced Search & Filters

## Phase 4

- Helmet Detection
- Triple Riding Detection
- Illegal Parking Detection
- Wrong Way Driving Detection

## Phase 5

- Accident Detection
- Automatic Evidence Generation
- Alert System
- Traffic Analytics

---

# 👨‍💻 Development Rules

- One module = One responsibility.
- Keep business logic outside API routes.
- Frontend communicates only with the backend.
- Backend communicates with PostgreSQL.
- No SQL queries outside `crud.py`.
- Store all configurations inside `config.py`.
- Every module should be independently testable.
- Keep the project modular and scalable.

---

# 📌 Current Status

- ✅ Project Planning Completed
- ✅ Project Architecture Designed
- ⬜ Backend Setup
- ⬜ FastAPI Integration
- ⬜ Streamlit Frontend
- ⬜ RTSP Camera Integration
- ⬜ Vehicle Detection
- ⬜ Number Plate Detection
- ⬜ OCR Integration
- ⬜ PostgreSQL Integration
- ⬜ Frontend–Backend API Integration
- ⬜ Testing