# 🏰 Fortress AI

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=nextdotjs&logoColor=white)](https://nextjs.org/)
[![Clerk](https://img.shields.io/badge/Auth-Clerk-6C47FF?style=for-the-badge&logo=clerk)](https://clerk.com/)
[![ROCm](https://img.shields.io/badge/ROCm-ED1C24?style=for-the-badge&logo=amd&logoColor=white)](https://www.amd.com/en/graphics/servers-solutions-rocm)

**Fortress AI** is a private, high-performance, multi-agent legal audit system designed to run on **AMD MI300X** servers. It leverages the latest in ROCm-accelerated inference to provide a secure "Command Center" for complex legal document analysis.
  
---

## 🚀 Key Features

- **Unified Qwen Pipeline**: Orchestrated via LangGraph, utilizing **Qwen-3.6** for structured extraction, risk analysis, and report synthesis.
- **Hardware-Aware Design**: Optimized for ROCm 7.x and AMD MI300X clusters via vLLM.
- **High-Density RAG**: Integrated **Qdrant** vector database for multilingual legal context.
- **Enterprise Auth**: Secure user management and SSO via **Clerk**.
- **Live Streaming**: Real-time audit reports via Server-Sent Events (SSE).
- **Asynchronous Processing**: Background tasks powered by **Celery** and **Redis**.
- **Advanced PDF Parsing**: **PyMuPDF**-powered extraction with layout-aware text, header detection, and table capture.

---

## 🛠 Tech Stack

### Backend
- **Framework**: FastAPI (Async)
- **Orchestration**: LangGraph (Multi-agent DAG)
- **Inference**: vLLM (OpenAI-compatible)
- **Database**: PostgreSQL (Prisma ORM) & Qdrant (Vector DB)
- **Task Queue**: Celery & Redis

### Frontend
- **Framework**: Next.js 15 (App Router)
- **Auth**: Clerk Next.js SDK
- **Styling**: Tailwind CSS v4 & shadcn/ui
- **Animations**: Framer Motion

---

## 📐 Architecture

Fortress AI utilizes a distributed, containerized architecture optimized for low-latency inference and high-fidelity legal analysis.

```mermaid
graph TD
    User([User / Browser])
    
    subgraph Frontend_Cloud [Frontend Container]
        NextJS[Next.js 15 App]
        Clerk[Clerk Auth SDK]
    end

    subgraph Backend_Cloud [Backend Infrastructure]
        API[FastAPI Gateway]
        LGraph[LangGraph Orchestrator]
        Celery[Celery Worker]
        Redis[(Redis Cache)]
    end

    subgraph AI_Cloud [Inference Engine]
        vLLM[vLLM Service]
        Qwen[[Qwen 3.6 - 27B]]
    end

    subgraph Data_Cloud [Persistence Layer]
        PG[(PostgreSQL)]
        Qdrant[(Qdrant Vector DB)]
    end

    User <--> NextJS
    NextJS -- Proxies API --> API
    NextJS -- Validates --> Clerk
    
    API <--> LGraph
    LGraph -- Inference --> vLLM
    vLLM -- ROCm Accelerated --> Qwen
    
    LGraph <--> Qdrant
    API <--> PG
    
    API -- Tasks --> Redis
    Redis <--> Celery
    Celery -- RAG / Audit --> LGraph
```

### 🧠 The Audit Pipeline
The system follows a 4-node "Chain of Thought" process orchestrated by **LangGraph**:   

1.  🔍 **Extraction Node**: Converts unstructured PDFs/Docs into clean legal primitives (parties, dates, clauses).
2.  📚 **Research Node**: Performs semantic search against the **Qdrant** store for precedents and statutory context.
3.  ⚠️ **Risk Node**: Cross-references clauses against a risk matrix to identify liabilities and red flags.
4.  📝 **Reporter Node**: Synthesizes the analysis into a professional, human-readable audit report via SSE.

---

## 🛡 License
Private / Proprietary — All rights reserved.
