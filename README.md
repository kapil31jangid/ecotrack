# 🌱 EcoTrack — AI Carbon Footprint Tracker
> *Powered entirely by Google Cloud · Zero third-party AI dependencies*

## Chosen Vertical
Personal Sustainability Assistant

## Problem Statement
Climate change requires urgent action, yet individuals often find sustainable living overwhelming. Urban professionals (aged 25-40) want to reduce their carbon footprint but lack a clear starting point. EcoTrack addresses this by providing instant footprint audits, comparing scores to regional and global baselines, and delivering personalized action tasks. Using Vertex AI Gemini, EcoTrack offers real-time sustainability coaching without any preachy or guilt-inducing rhetoric.

## Architecture

```
                                 ┌────────────────────────┐
                                 │       Client App       │
                                 │   (React + Vite UI)    │
                                 └───────────┬────────────┘
                                             │ HTTP Requests
                                             ▼
                                 ┌────────────────────────┐
                                 │   Nginx Reverse Proxy  │
                                 │      (Port 8080)       │
                                 └───────────┬────────────┘
                                             │ Proxy Pass /api/
                                             ▼
                                 ┌────────────────────────┐
                                 │   FastAPI Web Server   │
                                 │      (Port 8000)       │
                                 └─────┬─────┬──────┬─────┘
                                       │     │      │
          ┌────────────────────────────┘     │      └────────────────────────────┐
          ▼                                  ▼                                   ▼
┌──────────────────┐                ┌──────────────────┐               ┌──────────────────┐
│  Firestore DB    │                │ Vertex AI Gemini │               │ Cloud Logging &  │
│  (User Records)  │                │  (AI chat coach) │               │   Cloud Trace    │
└──────────────────┘                └──────────────────┘               └──────────────────┘
```

## Google Cloud Services (10 total)

| # | Service | Purpose |
|---|---------|---------|
| 1 | **Cloud Run** | Hosts the multi-stage, containerized FastAPI + React app in a serverless, scalable environment. |
| 2 | **Vertex AI Gemini** | Serves as the sole AI provider for personalized sustainability coaching (Gemini 1.5 Flash & 1.0 Pro). |
| 3 | **Firestore** | Stores user footprint history and conversational chat logs. |
| 4 | **Artifact Registry** | Securely stores built Docker container images for deployment. |
| 5 | **Cloud Build** | Runs automated tests, builds images, and coordinates CI/CD deployments. |
| 6 | **Cloud Logging** | Consolidates application execution and Gemini model usage audits. |
| 7 | **Cloud Monitoring** | Controls uptime checks and resource alert loops. |
| 8 | **Cloud Trace** | Performs request span monitoring for API operations. |
| 9 | **Cloud Scheduler** | Triggers weekly analytical aggregation tasks. |
| 10| **Secret Manager** | Provides future-proof secure token and credential storage. |

## AI Provider: Google Vertex AI Gemini
- **Primary Model**: `gemini-1.5-flash` (for fast and cost-efficient completions)
- **Fallback Model**: `gemini-1.0-pro` (to ensure high availability if the primary fails)
- **Authentication**: IAM-based default credentials (requires `roles/aiplatform.user` on the runtime service account) — absolutely no API keys are required.
- **Safety Filters**: Blocking settings enabled across harassment, hate speech, sexual content, and dangerous categories.

## How It Works
1. **Inputs**: The user inputs details regarding their weekly commute (km/week), diet type, monthly electricity usage (kWh), and shopping habits.
2. **Local Preview**: Client-side logic estimates emissions instantaneously, letting users see immediate impacts of changing inputs.
3. **Calculation & Audit**: Upon submission, the backend performs formal audits using localized factors and stores records asynchronously to Firestore.
4. **Insights Dashboard**: The dashboard displays interactive gauge scores, horizontal bar charts, and 5 personalized action tips ranked by highest emission impact.
5. **AI Chat Coach**: The user can open the chat panel to get real-time encouragement and carbon reduction strategies from Gemini AI, which dynamically receives the user's latest carbon context.

## Emission Calculation Methodology

| Category | Unit Factor | Source / Rationale |
|---|---|---|
| **Transport (Car)** | 0.21 kg CO2e / km | Average gasoline passenger sedan emissions. |
| **Transport (Bus)** | 0.089 kg CO2e / km | Medium-occupancy public transit multiplier. |
| **Transport (Flight)**| 0.255 kg CO2e / km | Commercial short/medium haul passenger flight intensity. |
| **Diet (Vegan)** | 55.0 kg CO2e / month | Plant-based lifestyle footprint index. |
| **Diet (Vegetarian)**| 85.0 kg CO2e / month | Dairy-inclusive vegetable diet index. |
| **Diet (Omnivore)**  | 150.0 kg CO2e / month | Standard balanced meat and produce diet. |
| **Diet (Meat-Heavy)**| 230.0 kg CO2e / month | High red meat consumption baseline. |
| **Energy (Electricity)**| 0.82 kg CO2e / kWh | Grid-intensity baseline for India. |
| **Shopping (Low)**   | 30.0 kg CO2e / month | Minimalist consumption index. |
| **Shopping (Medium)**| 70.0 kg CO2e / month | Standard purchasing baseline. |
| **Shopping (High)**  | 130.0 kg CO2e / month | High consumerism/fast fashion baseline. |

## Local Development

1. **Clone the repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/ecotrack
   cd ecotrack
   ```

2. **Setup Env**:
   ```bash
   cp .env.example .env
   # Add your Google Cloud project ID to GOOGLE_CLOUD_PROJECT in .env
   ```

3. **Authenticate Vertex AI locally**:
   Ensure you have the Google Cloud SDK installed, then authenticate your local CLI environment:
   ```bash
   gcloud auth application-default login
   ```

4. **Build and Run via Docker Compose**:
   ```bash
   docker compose up --build
   ```
   Open [http://localhost:8080](http://localhost:8080) to test the application.

### Running Separately (Without Docker)

For faster hot-reloading and development loops, you can run the frontend and backend services separately:

1. **Start the Backend (FastAPI)**:
   - Create a virtual environment and activate it:
     ```bash
     cd backend
     python -m venv venv
     # Windows (PowerShell):
     .\venv\Scripts\Activate.ps1
     # macOS/Linux:
     source venv/bin/activate
     ```
   - Install dependencies:
     ```bash
     pip install -r requirements.txt
     ```
   - Start Uvicorn:
     ```bash
     uvicorn main:app --host 127.0.0.1 --port 8000 --reload
     ```
     The backend API will run on [http://localhost:8000](http://localhost:8000).

2. **Start the Frontend (Vite)**:
   - Navigate to the frontend folder:
     ```bash
     cd frontend
     ```
   - Install node packages:
     ```bash
     npm install
     ```
   - Start the Vite development server:
     ```bash
     npm run dev
     ```
     The frontend dev server will spin up on [http://localhost:5173](http://localhost:5173) and proxy `/api/*` requests to the Uvicorn backend automatically.

## Deploy to GCP

Run the provided setup script with your target Google Cloud Project ID:
```bash
chmod +x deploy/setup-gcp.sh
./deploy/setup-gcp.sh YOUR_GCP_PROJECT_ID
```
The script will configure all APIs, provisioning database, service accounts, IAM bindings, build/push container, and deploy to Cloud Run.

## CI/CD

To configure continuous deployment:
1. Go to **Cloud Build** in the GCP Console.
2. Select **Triggers** and click **Create Trigger**.
3. Authenticate and connect your GitHub repository.
4. Set the build configuration file type to **Cloud Build configuration file (yaml)** and point to `cloudbuild.yaml`.
5. Set the trigger to run on commits to the `^main$` branch.

## Running Tests

### Backend Tests (Pytest)
```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```

### Frontend Tests (Vitest)
```bash
cd frontend
npm install
npm run test
```

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `GOOGLE_CLOUD_PROJECT` | GCP Project ID used for Firestore and Vertex AI initialization. | `""` (runs backend in mock/in-memory mode if empty) |
| `FIRESTORE_COLLECTION` | Target collection name for carbon records. | `footprints` |
| `VITE_API_BASE_URL` | Base URL routing for frontend fetch requests. | `/api` |

## Security
- **No API Keys**: Vertex AI and Firestore auth uses Google's recommended IAM role delegations (`roles/aiplatform.user` and `roles/datastore.user`), removing key management risks.
- **Sanitized Failures**: Global exception handlers capture traceback logs server-side and only return clean JSON messages with unique request IDs to the browser.
- **Input Constraints**: All values parsed by the backend are strictly validated using Pydantic schemas.
- **Rate-Limiting**: Global rate-limits protect endpoints from scrapers or spam (60/min global, 10/min on AI chat).
- **Git Protections**: `.gitignore` is pre-configured to exclude local secrets and key files.

## Assumptions
- **Electricity factor**: Calculation uses India grid intensity (0.82 kg CO2e/kWh).
- **Commute patterns**: Range sliders assume maximum weekly commute bounds of 5,000 km.
- **Session state**: Unauthenticated session states are tracked via browser localStorage using unique UUIDs.
- **Vertex AI location**: SDK calls default to the `asia-south1` region.
