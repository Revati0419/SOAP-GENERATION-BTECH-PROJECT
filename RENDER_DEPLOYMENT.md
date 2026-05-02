# Render Deployment Guide for SOAP Generation Backend

## Prerequisites
1. GitHub account with your repository pushed
2. Render account (sign up at https://render.com)

## Step-by-Step Deployment

### Step 1: Push Your Code to GitHub
First, ensure all your changes are committed and pushed to your GitHub repository:

```bash
git add .
git commit -m "Prepare for Render deployment"
git push origin Tanuja
```

### Step 2: Create a New Web Service on Render
1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **New +** → **Web Service**
3. Connect your GitHub account if not already connected
4. Select your **SOAP-GENERATION-BTECH-PROJECT** repository
5. Click **Connect**

### Step 3: Configure the Service
Fill in the following details:

| Setting | Value |
|---------|-------|
| **Name** | soap-generation-api |
| **Environment** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn api_server:app --host 0.0.0.0 --port $PORT` |
| **Plan** | Free (or upgrade if needed) |

### Step 4: Set Environment Variables (Optional)
If your application needs environment variables:
1. Scroll down to **Environment** section
2. Click **Add Environment Variable**
3. Add any required variables (e.g., `LOG_LEVEL=INFO`)

### Step 5: Deploy
1. Click **Create Web Service**
2. Render will automatically start building and deploying your application
3. Monitor the build logs in real-time on the dashboard
4. Once deployed, you'll get a unique URL like `https://soap-generation-api-xxxx.onrender.com`

## Testing Your Deployment

Once deployed, test your API:

```bash
curl https://soap-generation-api-xxxx.onrender.com/api/stats
```

Or use the `/api/generate-from-transcript` endpoint:

```bash
curl -X POST https://soap-generation-api-xxxx.onrender.com/api/generate-from-transcript \
  -H "Content-Type: application/json" \
  -d '{
    "conversation": "डॉक्टर: तुम्हाला कसे वाटते?\nरुग्ण: मला झोप येत नाही...",
    "phq8_score": 15,
    "severity": "moderate",
    "gender": "female",
    "target_lang": "marathi"
  }'
```

## Important Notes

### Model Loading
- **First Request**: The first API request may take 2-5 minutes as the Gemma 2b model and translation model are loaded into memory
- **Subsequent Requests**: Will be much faster as models are cached in memory

### Memory Considerations
- The free tier has limited memory. If you encounter out-of-memory errors:
  - Upgrade to a paid Render plan
  - Optimize model loading
  - Use model quantization

### Database Persistence
- Your SQLite database (`data/clinic.db`) will be lost when the service restarts
- For persistent storage, consider:
  - Using Render's PostgreSQL add-on
  - Modifying your code to use PostgreSQL instead of SQLite

### Custom Domain
- To use a custom domain:
  1. Go to your service settings
  2. Scroll to **Custom Domains**
  3. Add your domain and follow the DNS configuration instructions

## Troubleshooting

### Build Fails
- Check the build logs on Render dashboard
- Ensure `requirements.txt` has compatible versions
- Verify `runtime.txt` is correct

### Application Crashes
- Check the logs: Click **Logs** tab on Render dashboard
- Common issues:
  - Out of memory: Upgrade plan or reduce model size
  - Missing environment variables: Add them in the Environment section
  - Port issues: Ensure start command uses `$PORT` environment variable

### Model Loading Timeout
- First request may timeout due to model download
- Increase timeout settings in your client
- Consider pre-warming models on deployment

## Monitoring

1. **View Logs**: Click **Logs** tab to see real-time logs
2. **Service Health**: Check the status indicator at the top
3. **Metrics**: View CPU, memory, and disk usage in the **Metrics** tab

## Next Steps

1. **Configure Frontend**: Update your React frontend to point to the Render URL
2. **Add Database**: Consider adding PostgreSQL for persistent storage
3. **Custom Domain**: Set up a custom domain if needed
4. **Scaling**: Monitor usage and upgrade plan if needed

---

**Need help?** Visit [Render Documentation](https://render.com/docs)
