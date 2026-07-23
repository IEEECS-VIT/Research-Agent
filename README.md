![ieeecs-template-header](https://github.com/user-attachments/assets/c3c40c85-51a2-4a5e-82a4-c32a0223e336)

<h1 align="center">Research Alignment Agent</h1>

<h4 align="center">An AI-powered system for analyzing academic papers, detecting alignment or contradictions, and maintaining research consistency over time.</h4>

---

## Overview

Academic research often involves referencing multiple papers across different timelines, making it difficult to ensure consistency and alignment between sources.

This project aims to build a **research alignment agent** that helps users analyze academic papers, compare new research with previously referenced work, and detect agreements or contradictions.

The system allows users to upload drafts, topics, and reference papers, while maintaining a long-term contextual memory. When new research is introduced, it evaluates whether it aligns with or contradicts earlier work—even if those references were added weeks earlier.

---

## Core Features

* Upload research papers, drafts, and topics
* Generate embeddings and maintain long-term memory
* Detect alignment or contradiction between research papers
* Summarize academic documents
* Answer relevance-based queries
* Suggest references based on highlighted sections
* Context-aware reasoning across time

---

## Architecture Overview

The system consists of the following components:

* **Input Module**
  Handles user uploads (PDFs, drafts, topics)

* **Embedding Engine**
  Converts documents into vector representations

* **Vector Database (Memory Layer)**
  Stores embeddings for long-term contextual retrieval

* **Alignment Engine**
  Compares new inputs with stored research and detects alignment or contradiction

* **LLM Module**
  Generates summaries, explanations, and answers queries

* **Query Interface / API Layer**
  Enables interaction with the system

### Data Flow

1. User uploads documents or drafts
2. Documents are processed and converted into embeddings
3. Embeddings are stored in a vector database
4. New documents are compared with existing memory
5. Alignment or contradiction is detected
6. Results are returned with summaries and explanations

---

## Tech Stack

| Layer       | Technology Used               |
| ----------- | ----------------------------- |
| Backend     | Python (FastAPI)              |
| LLM         | OpenAI API                    |
| Embeddings  | OpenAI / SentenceTransformers |
| Database    | FAISS / Pinecone              |
| DevOps      | Docker, GitHub Actions        |
| Other Tools | LangChain / LlamaIndex        |

---

## Project Structure

```bash
app/                    # FastAPI backend
├── api/                # REST API routes
│   ├── auth.py         # Firebase auth endpoints
│   ├── documents.py    # Document upload/list/delete
│   ├── analysis.py     # Analysis sessions & comparisons
│   └── health.py       # Health check
├── core/               # Config, database, security
├── models/             # SQLAlchemy models
├── schemas/            # Pydantic request/response schemas
├── services/           # Business logic layer
└── utils/              # Firebase Admin SDK

frontend/               # React + Vite + Tailwind
├── src/
│   ├── components/     # Layout, common UI components
│   ├── contexts/       # Auth, Theme (dark/light)
│   ├── pages/          # Login, Dashboard, Upload, Analysis, Settings
│   └── services/       # API client, Firebase config

ingestion_pipeline/     # PDF parsing + summarization (Docling + Gemini)
GraphEngine/            # Comparison engine (graph DB, retrieval, analyst/verifier)

Dockerfile & docker-compose.yml  # Containerization
```

---

## ⚙️ Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Research-Agent
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
cp .env.example .env
```

Update `.env` with your credentials.

### 4. Run the Project

```bash
uvicorn src.api.main:app --reload
```

---

## Docker Setup

### Build Image

```bash
docker build -t research-agent .
```

### Run Container

```bash
docker run -p 8000:8000 research-agent
```

---

## Git Hooks Setup

This repository uses custom Git hooks to enforce commit standards and workflow discipline.

After cloning the repository, run:

```bash
git config core.hooksPath .githooks
```

This enables:

* Commit message validation
* Pre-push checks

---

## Environment Variables

| Variable                  | Description                          |
| ------------------------- | ------------------------------------ |
| GEMINI_API_KEY            | Google Gemini API key for LLM access |
| FIREBASE_CREDENTIALS_PATH | Firebase Admin SDK credentials       |
| FIREBASE_PROJECT_ID       | Firebase project ID                  |
| FIREBASE_API_KEY          | Firebase Web API key                 |
| DATABASE_URL              | SQLite/PostgreSQL URL                |
| PORT                      | Application port                     |

---

## Example Use Case

1. User uploads a draft paper and reference materials
2. System stores and embeds key ideas
3. Weeks later, user uploads a new research paper
4. System detects contradictions with previously cited work
5. User receives a detailed explanation and summary
6. User highlights a section → system suggests relevant references

---

## Frontend Setup

The frontend is a React + Vite + TypeScript app with Tailwind CSS.

```bash
cd frontend
cp .env.example .env   # Fill in Firebase config
npm install
npm run dev            # Development on port 5173
```

The frontend proxies `/api` requests to the backend (port 8000) via Vite's dev server.

---

## Deployment

* Containerized using Docker
* Can be deployed on AWS / GCP / Azure
* CI/CD handled via GitHub Actions

---

## Testing

```bash
pytest
```

---

## Project Status

🟢 In Development

---

## Contributing

Please refer to `CONTRIBUTING.md` for contribution guidelines.

---

## License

This project is licensed under the terms of the MIT License.
