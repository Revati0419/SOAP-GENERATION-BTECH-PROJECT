flowchart TD
    subgraph Frontend [React + Vite]
        U[Upload JSON / Transcript]
    end

    subgraph API [FastAPI :8000]
        A[/POST /api/generate-from-json/\nPOST /api/generate-from-transcript/]
    end

    U -->|multipart/form-data| A

    subgraph Generator [MultilingualSOAPGenerator]
        D[LanguageDetector\n(has_english?)]
        P1[Phase 1\n(text_en present)]
        P2[Phase 2\n(Marathi-only)]
        F1[Format English turns (40 cap)]
        F2[Format Marathi turns (40 cap)]
        NER[IndicNER\n+ Marathi regex]
        RAG[ChromaDB search\nMiniLM-L6 embeddings]
        MT1[NLLB-200\nMR→EN\n(for convo)]
        LLM[Gemma 2B via Ollama\nSOAP S/O/A/P]
        MT2[NLLB-200\nEN→target\n(per section)]
    end

    A --> D
    D -->|has text_en| P1
    D -->|no text_en| P2

    P1 --> F1 --> LLM
    P2 --> F2 --> NER --> RAG --> MT1 --> LLM

    LLM --> MT2 --> OUT[Response JSON\nsoap_english + soap_<target>\ninput_language, target_language,\nmetadata (processing_time)]