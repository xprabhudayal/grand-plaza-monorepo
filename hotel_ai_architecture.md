# **Hotel Room Service AI Concierge \- Fullstack Architecture Document**

## **Introduction**

This document outlines the complete fullstack architecture for the Hotel Room Service AI Concierge. It covers the backend services, the voice AI pipeline, the frontend implementation, and their integration points. It serves as the single source of truth for the 2-day proof-of-concept development, ensuring consistency across the entire technology stack.

### **Change Log**

| Date | Version | Description | Author |
| :---- | :---- | :---- | :---- |
| 2025-08-12 | 1.0 | Initial Draft | Architect |

## **High-Level Architecture**

### **Technical Summary**

The system is a real-time, voice-first conversational application. The architecture consists of a Python backend powered by **FastAPI** (for standard REST API endpoints) and **Pipecat** (for managing the real-time voice/video conversation flow). The frontend is a **React/Next.js** application that uses the **Daily.co SDK** to handle the WebRTC video call. The **Tavus AI Avatar** is integrated as a video source within the Daily.co call, orchestrated by Pipecat. A local **SQLite** database managed by **Prisma ORM** will handle order persistence.

### **Platform and Infrastructure Choice**

For this 2-day PoC, speed and simplicity are paramount.

* **Platform:** We will use a PaaS (Platform as a Service) model for easy deployment.  
* **Frontend Hosting:** **Vercel**. It offers seamless, zero-config deployment for Next.js applications.  
* **Backend Hosting:** **Railway**. It provides simple deployment for Python/FastAPI applications and can manage the SQLite database file.  
* **Deployment Regions:** US-East.

### **Repository Structure**

* **Structure:** **Polyrepo**. A monorepo is overkill for this PoC. We will maintain two separate repositories: one for the frontend and one for the backend. This simplifies the development and deployment workflow for the tight timeline.

### **High-Level Architecture Diagram**

graph TD
    subgraph "Guest's Room"
        User -- "Interacts with" --> FE[Frontend App on Tablet<br>(React/Next.js on Vercel)];
    end

    subgraph "Real-time Communication Layer"
        FE <== "WebRTC Session" ==> Daily[Daily.co WebRTC];
        Pipecat[Pipecat Voice Pipeline<br>(on Railway)] -- "Manages Call" --> Daily;
        Tavus[Tavus AI Avatar Service] -- "Video Stream" --> Daily;
    end

    subgraph "Backend Services (on Railway)"
        Pipecat -- "Sends Final Order" --> API[FastAPI Backend];
        API -- "Reads/Writes" --> DB[(SQLite Database<br>Prisma ORM)];
    end

    subgraph "Hotel Staff"
        Admin -- "Views Orders" --> AdminFE[Admin Dashboard<br>(Part of Frontend App)];
        AdminFE -- "Fetches Orders" --> API;
    end

    User -- "Speaks/Listens" --> Pipecat;


### **Architectural Patterns**

* **Voice-First Interaction:** The UI is designed to supplement the primary voice conversation, not replace it.  
* **Real-time Communication (WebRTC):** Daily.co will manage the complexities of establishing and maintaining the video call between the guest and the AI.  
* **REST API:** A simple RESTful API will be used for standard data operations like saving an order and retrieving the menu/order list for the admin dashboard.

## **Tech Stack**

This table is the single source of truth for all technologies and versions to be used.

| Category | Technology | Version | Purpose |
| :---- | :---- | :---- | :---- |
| Frontend Framework | Next.js | 14.2.x | React framework for UI, routing, and Vercel deployment. |
| UI Library | React | 18.2.x | Core library for building UI components. |
| Styling | Tailwind CSS | 3.4.x | For rapid, utility-first styling of the UI. |
| WebRTC SDK | @daily-co/daily-js | 0.63.x | Client-side SDK to manage the video call. |
| Backend Framework | FastAPI | 0.111.x | High-performance Python framework for the REST API. |
| Voice AI Pipeline | Pipecat-AI | 0.1.11 | Framework for building the conversational voice flow. |
| Avatar Integration | pipecat-ai\[tavus\] | 0.1.11 | Pipecat extension for Tavus integration. |
| Database ORM | Prisma | 5.15.x | ORM for database schema management and access. |
| Database | SQLite | 3.x | Local, file-based database for the PoC. |
| ASGI Server | Uvicorn | 0.29.x | Server to run the FastAPI application. |

## **Data Models**

The primary data model is Order. The schema will be defined using Prisma.  
// prisma/schema.prisma

generator client {  
  provider \= "prisma-client-py"  
}

datasource db {  
  provider \= "sqlite"  
  url      \= "file:./dev.db"  
}

model Order {  
  id          String   @id @default(cuid())  
  roomNumber  String  
  bookingName String  
  items       Json     // Store ordered items as a JSON array  
  status      String   @default("confirmed")  
  referenceId String   @unique  
  createdAt   DateTime @default(now())  
}

## **API Specification**

The backend will expose a minimal set of REST endpoints.  
openapi: 3.0.0  
info:  
  title: Hotel Concierge API  
  version: 1.0.0  
paths:  
  /menu:  
    get:  
      summary: Get available menu items  
      responses:  
        '200':  
          description: A list of menu items.  
          content:  
            application/json:  
              schema:  
                type: array  
                items:  
                  type: object  
                  properties:  
                    name: { type: string }  
                    price: { type: number }  
  /order:  
    post:  
      summary: Place a new order  
      requestBody:  
        required: true  
        content:  
          application/json:  
            schema:  
              type: object  
              properties:  
                roomNumber: { type: string }  
                bookingName: { type: string }  
                items: { type: array, items: { type: string } }  
      responses:  
        '201':  
          description: Order created successfully.  
          content:  
            application/json:  
              schema:  
                type: object  
                properties:  
                  message: { type: string }  
                  referenceId: { type: string }  
  /admin/orders:  
    get:  
      summary: Get all orders for the admin dashboard  
      security:  
        \- BasicAuth: \[\]  
      responses:  
        '200':  
          description: A list of all orders.  
components:  
  securitySchemes:  
    BasicAuth:  
      type: http  
      scheme: basic

## **Components**

* **Frontend (React/Next.js App):** Responsible for rendering the UI, managing the Daily.co video call, displaying live transcription, and showing order status.  
* **Backend (FastAPI Server):** Responsible for persisting orders to the database and serving data to the admin dashboard.  
* **Voice Pipeline (Pipecat Service):** A Python service that connects to the Daily.co call. It handles STT, LLM processing, TTS, and orchestrates the Tavus avatar video stream. It is the "brain" of the conversation.  
* **WebRTC Service (Daily.co):** The cloud service that provides the real-time video and audio transport layer.

## **Core Workflows**

### **Place Order Sequence Diagram**

sequenceDiagram
    participant Guest
    participant Frontend
    participant Daily
    participant Pipecat
    participant Tavus
    participant API
    participant DB

    Guest->>Frontend: Initiates Call
    Frontend->>Daily: Create & Join Room
    Daily-->>Pipecat: Invite AI Participant
    Pipecat->>Tavus: Start Avatar Video Stream
    Tavus-->>Daily: Send Video to Room
    Pipecat->>Guest: TTS Greeting via Daily
    Guest->>Pipecat: Speaks Order via Daily
    Pipecat->>Pipecat: Process Speech (STT -> LLM -> TTS)
    Pipecat->>Guest: Asks for Room/Name
    Guest->>Pipecat: Provides Details
    Pipecat->>API: POST /order with final details
    API->>DB: Store Order in SQLite via Prisma
    DB-->>API: Return Success
    API-->>Pipecat: Return referenceId
    Pipecat->>Guest: TTS Confirmation with referenceId

## **Unified Project Structure (Polyrepo)**

**Backend Repository (concierge-backend):**  
/concierge-backend  
├── app/  
│   ├── main.py             \# FastAPI app setup and routes  
│   ├── services.py         \# Business logic (order creation)  
│   └── pipeline.py         \# Pipecat conversational flow logic  
├── prisma/  
│   ├── schema.prisma       \# Database schema  
│   └── dev.db              \# SQLite database file  
├── .env                    \# Environment variables  
├── requirements.txt        \# Python dependencies  
└── Dockerfile              \# For containerized deployment

**Frontend Repository (concierge-frontend):**  
/concierge-frontend  
├── pages/  
│   ├── index.js            \# Main guest UI page  
│   └── admin.js            \# Admin dashboard page  
├── components/  
│   ├── VideoAvatar.js  
│   ├── TranscriptionView.js  
│   └── OrderSummaryCard.js  
├── styles/  
│   └── globals.css         \# Tailwind CSS setup  
├── public/  
├── .env.local              \# Frontend environment variables  
└── package.json

## **Development Workflow**

1. **Backend Setup:**  
   * python \-m venv venv  
   * source venv/bin/activate  
   * pip install \-r requirements.txt  
   * prisma generate  
   * prisma db push  
   * uvicorn app.main:app \--reload  
2. **Frontend Setup:**  
   * npm install  
   * npm run dev

## **Deployment Architecture**

* **Frontend:** The Next.js app will be connected to a Vercel project. Pushing to the main branch will trigger an automatic build and deployment.  
* **Backend:** The FastAPI app will be connected to a Railway project. Railway will run the uvicorn command to start the server. The dev.db file will be persisted across deployments.

## **Security and Performance**

* **Security:** The /admin/orders endpoint will be protected by basic authentication for the PoC. All other security concerns are out of scope.  
* **Performance:** Performance optimization is out of scope for the 2-day PoC.

## **Coding Standards**

* **Environment Variables:** All sensitive information (API keys for Daily.co, Tavus) MUST be stored in .env files and not hardcoded.  
* **Styling:** The frontend will use Tailwind CSS. A globals.css file will define the base styles and the light/dark theme variables using CSS custom properties.  
* **API:** Backend code should use async/await for all I/O operations.

## **Next Steps**

1. **Developer Handoff:** The developer agent can now begin implementation.  
2. **Build Order:**  
   1. Implement the **FastAPI backend** and Prisma schema first.  
   2. Develop the core **Pipecat pipeline** logic.  
   3. Build the **React/Next.js frontend** and integrate the Daily.co SDK last.