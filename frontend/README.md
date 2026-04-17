# SOAP Frontend (React + Vite)

This frontend provides the UI for:
- JSON session → SOAP generation
- Audio transcription (Whisper via backend)
- End-to-end audio → SOAP
- Transcript-first multilingual SOAP generation

## Prerequisites

- Node.js 18+
- Backend API running on port `8000` (default)

## Setup

1. Install dependencies:
	`npm install`
2. Configure environment:
	- Copy `.env.example` to `.env`
	- Update `VITE_API_BASE_URL` if backend is not `http://localhost:8000`

## Run

- Development server: `npm run dev`
- Production build: `npm run build`
- Preview build: `npm run preview`
- Lint: `npm run lint`

## API Configuration

The app reads backend URL from:

- `VITE_API_BASE_URL`

Fallback (when missing):

- `http://localhost:8000`

This config is centralized in `src/lib/api.js`.
