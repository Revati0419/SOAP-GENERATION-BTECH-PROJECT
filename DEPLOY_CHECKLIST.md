# Quick Deployment Checklist for Render

## ✅ Files Created for Render Deployment

1. **render.yaml** - Render configuration file
2. **runtime.txt** - Python version specification
3. **.renderignore** - Files to exclude from deployment
4. **RENDER_DEPLOYMENT.md** - Detailed deployment guide
5. **.env.example** - Environment variables reference

## ✅ Code Updates

- Updated `api_server.py` to read the `PORT` environment variable
- This ensures compatibility with Render's port assignment

## ✅ Simplified dependencies

- `requirements.txt` has been reduced to only essential packages (32 packages)
- Using CPU-only PyTorch version for compatibility

## 🚀 Quick Start - Deploy in 5 Steps

### 1. Commit and Push to GitHub
```bash
cd "~/Desktop/Btech Project/BTECH PROJECT/Version 1.0/SOAP-GENERATION-BTECH-PROJECT"
git add .
git commit -m "Setup for Render deployment"
git push origin Tanuja
```

### 2. Sign Up on Render
Go to https://render.com and create a free account

### 3. Create New Web Service
- Click **New +** → **Web Service**
- Connect your GitHub account
- Select your repository

### 4. Configure Service
- **Name**: `soap-generation-api`
- **Runtime**: Python 3
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn api_server:app --host 0.0.0.0 --port $PORT`
- **Plan**: Free (or upgrade later)

### 5. Deploy
- Click **Create Web Service**
- Wait for build to complete (~5-10 minutes)
- Get your public URL

## 📋 What Gets Deployed

✅ **Included:**
- FastAPI server with all API endpoints
- Gemma 2b model (loaded on first request)
- NLLB translation model (Facebook/Meta)
- RAG (Retrieval Augmented Generation)
- NER (Named Entity Recognition)
- Indic language support (Marathi, Hindi)
- SOAP generation pipeline

❌ **Excluded:**
- Whisper ASR (audio transcription)
- Jupyter notebooks
- Documentation files
- Node.js frontend (deploy separately)

## ⚠️ Important Notes

### First Request Takes Time
- First API request will take 2-5 minutes
- Models are downloaded and cached during this time
- Subsequent requests are fast

### Model Limitations
- Free Render tier has limited memory (~512MB)
- If you get out-of-memory errors, upgrade to paid plan
- Each new deployment restarts the service and clears model cache

### Database
- SQLite database is **not persistent** on free tier
- Data resets when service restarts
- For production, integrate PostgreSQL

## 🔗 Test Your API

Once deployed, test with:

```bash
curl https://your-app.onrender.com/api/stats

# Generate SOAP notes
curl -X POST https://your-app.onrender.com/api/generate-from-transcript \
  -H "Content-Type: application/json" \
  -d '{
    "conversation": "डॉक्टर: कसे आहात?\nरुग्ण: माझे डोके दुखते...",
    "target_lang": "marathi"
  }'
```

## 📊 Monitoring

- **Logs**: View in Render dashboard under "Logs" tab
- **Metrics**: Check CPU, memory, and request count
- **Build History**: See all deployments and their status

## ❓ Troubleshooting

| Issue | Solution |
|-------|----------|
| Build fails | Check logs, verify requirements.txt |
| Out of memory | Upgrade to paid plan |
| First request timeout | Wait longer (models loading), or upgrade |
| Models not loading | Check logs for download errors |

---

**Questions?** Refer to `RENDER_DEPLOYMENT.md` for detailed instructions
