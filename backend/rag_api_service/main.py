from fastapi import FastAPI
import uvicorn
from routes.upload_pdf_routes import router
from routes.s3_pdf_routes import router as s3_router
  # Use underscores instead of hyphens

app = FastAPI(title="RAG API Service")  # Updated title to match your project name

# Register routes
app.include_router(router)
app.include_router(s3_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)