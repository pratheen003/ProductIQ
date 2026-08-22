# ProductIQ — Deployment & Infrastructure Guide
## Production & Staging Deployment Procedure (Post-Freeze Phase)

> **Important Deployment Notice:** Per the Hackathon Submission Roadmap, actual cloud deployment occurs immediately following the engineering documentation freeze. All live URLs, hostnames, and deployment endpoints below are literal placeholders to be populated upon live provisioning.

---

## 1. Deployment Target Summary

| Component | Target Runtime | Build / Start Command | Deployment Endpoint Placeholder |
|---|---|---|---|
| **Frontend UI** | Next.js 14 (Node.js 18+) | `npm run build && npm run start` | `<FRONTEND_DEPLOYED_URL_TO_BE_FILLED_AFTER_DEPLOYMENT>` |
| **Backend API** | FastAPI / Uvicorn (Python 3.10+) | `uvicorn productiq.api.app:app --host 0.0.0.0 --port 8000` | `<BACKEND_DEPLOYED_URL_TO_BE_FILLED_AFTER_DEPLOYMENT>` |
| **Data Storage** | Local / Volume Mounted JSON & Artifacts | Native file system persistence | `<MOUNTED_DATA_DIRECTORY_PATH>` |

---

## 2. Environment Variables & Secrets Configuration

All sensitive API keys and provider tokens are injected exclusively via secure environment variables. No secrets are committed to Git.

### Backend Environment Configuration (`.env`):
```env
# Application Environment
ENVIRONMENT=<TO_BE_CONFIGURED_e.g._production>
PORT=8000
LOG_LEVEL=INFO

# Grounded AI Enrichment Providers (Phase 4 Motor Intelligence)
GROQ_API_KEY=<TO_BE_INJECTED_GROQ_KEY>
OPENAI_API_KEY=<TO_BE_INJECTED_OPENAI_KEY>
LLM_PROVIDER=groq

# CORS & Allowed Origins
CORS_ORIGINS=<FRONTEND_DEPLOYED_URL_TO_BE_FILLED_AFTER_DEPLOYMENT>,http://localhost:3000
```

### Frontend Environment Configuration (`frontend/.env.production`):
```env
NEXT_PUBLIC_API_URL=<BACKEND_DEPLOYED_URL_TO_BE_FILLED_AFTER_DEPLOYMENT>
```

---

## 3. Step-by-Step Deployment Procedure

### A. Backend Deployment (Render / Railway / AWS ECS / Fly.io):
1. **Repository Setup:** Connect GitHub repository `https://github.com/pratheen003/ProductIQ.git` (branch: `main`).
2. **Environment Setup:** Set Python runtime to `3.10+`.
3. **Dependency Installation:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Data Verification:** Ensure `data/catalog/input/`, `data/catalog/ground_truth/`, and `data/catalog/lookups/` are packaged in the image or volume.
5. **Start Command:**
   ```bash
   uvicorn productiq.api.app:app --host 0.0.0.0 --port $PORT
   ```
6. **Health Check Endpoint:**
   ```http
   GET /api/health
   GET /api/catalog/health
   ```

### B. Frontend Deployment (Vercel / Netlify / Node.js Host):
1. **Root Directory:** Configure root directory as `frontend/`.
2. **Framework Preset:** Next.js (App Router).
3. **Build Command:**
   ```bash
   npm run build
   ```
4. **Output Directory:** `.next`
5. **Environment Variable:** Set `NEXT_PUBLIC_API_URL` to the provisioned backend URL.

---

## 4. Post-Deployment Verification Checklist

Upon completing cloud provisioning, verify the following:
- [ ] Backend health check responds `200 OK` at `<BACKEND_DEPLOYED_URL>/api/health`.
- [ ] Catalog health check confirms 1,000 input rows loaded at `<BACKEND_DEPLOYED_URL>/api/catalog/health`.
- [ ] Frontend loads smoothly at `<FRONTEND_DEPLOYED_URL>` with zero console errors.
- [ ] Catalog Batch Dashboard displays live 1,000-row metrics and conflict charts.
- [ ] Delivery format export button successfully downloads `productiq_delivery_output.xlsx` from the live frontend.
- [ ] Motor Intelligence dashboard displays the 12 motor catalog items and the interactive conflict comparator.

---

## 5. Live Deployment Metadata (To Be Updated)

- **Deployed Frontend URL:** `<TO BE FILLED AFTER DEPLOYMENT>`
- **Deployed Backend API URL:** `<TO BE FILLED AFTER DEPLOYMENT>`
- **Deployed Swagger Docs:** `<TO BE FILLED AFTER DEPLOYMENT>/docs`
- **Deployment Platform:** `<TO BE FILLED AFTER DEPLOYMENT>`
- **Deployment Timestamp:** `<TO BE FILLED AFTER DEPLOYMENT>`
