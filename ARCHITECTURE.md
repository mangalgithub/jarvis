# Jarvis Technical Architecture 🏗️

This document outlines the system architecture, data flow, and API specifications for the Jarvis Personal OS.

## 📐 System Diagram

```mermaid
graph TD
    subgraph Client_Layer [Frontend - Next.js]
        UI[Dashboard & Chat UI]
        STT[Speech-to-Text]
        WS_Client[WebSocket Client]
    end

    subgraph API_Gateway [Backend - Express.js]
        Auth[Authentication & JWT]
        RateLimit[Rate Limiting]
        DB_Proxy[Database Controller]
        WS_Server[Socket.io Server]
    end

    subgraph AI_Core [Agent Service - FastAPI]
        Orch[Jarvis Orchestrator]
        Vision[Vision Service - Gemini 2.5]
        Intent[Intent Classifier - Groq/LLama 3]
        
        subgraph Agents [Specialized Agents]
            FA[Finance Agent]
            HA[Health Agent]
            SA[Stock Agent]
            NA[News Agent]
            MA[Memory Agent]
        end
    end

    subgraph Data_Storage [Persistence]
        MDB[(MongoDB Atlas)]
    end

    %% Flow
    UI -->|REST /chat| Auth
    Auth -->|Proxy| Orch
    Orch -->|Multimodal Analysis| Vision
    Orch -->|Command Parsing| Intent
    Intent -->|Route| Agents
    
    Agents -->|Read/Write| MDB
    Auth -->|Notify| WS_Server
    WS_Server -->|Real-time Updates| WS_Client
    HA -->|Nutrition Data| MDB
    FA -->|Expense Data| MDB
```

---

## 🔌 API Specifications

### 1. Backend Gateway (Express)
| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/auth/register` | POST | User registration & JWT generation |
| `/api/auth/login` | POST | User authentication |
| `/api/chat` | POST | Main chat endpoint (handles text & base64 images) |
| `/api/dashboard` | GET | Aggregated data for all UI widgets |
| `/api/profile/memory` | GET | Retrieve all stored personal context |

### 2. Agent Service (FastAPI)
| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/agent/chat` | POST | Receives message + image, returns AI response & actions |
| `/agent/dashboard` | GET | Returns data specifically for health/finance charts |
| `/agent/news` | GET | Fetches and summarizes latest curated news |
| `/agent/memory` | POST | Manually update user preferences/dietary info |

---

## 🧠 Multimodal Logic Flow
1. **Input:** User sends a message (e.g., "Log this pizza") + a Base64 image.
2. **Vision Pre-processing:** The `Orchestrator` detects the image and calls `VisionService`.
3. **Context Injection:** The vision description (e.g., "[IMAGE ANALYSIS: Chicken Pizza, 800 cal]") is prepended to the user's message.
4. **Intent Detection:** The `IntentClassifier` sees the injected context and routes the request to the `HealthAgent`.
5. **Action Execution:** The `HealthAgent` parses the nutrition data and saves it to MongoDB.
6. **Real-time Update:** The backend emits a WebSocket event to refresh the Frontend charts instantly.

---

## 🛠️ Technology Stack
- **Frontend:** Next.js 15, Tailwind CSS, Framer Motion, Recharts.
- **Backend:** Node.js, Express, Socket.io, MongoDB Atlas.
- **AI Intelligence:** Python 3.12, FastAPI, LangChain, Gemini 2.5 Flash, Groq, Sentence-Transformers.
- **Infrastructure:** Docker (Hugging Face Spaces), Vercel.
