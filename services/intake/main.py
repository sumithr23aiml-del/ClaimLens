from fastapi import FastAPI
from .routes import router

app = FastAPI(
    title="ClaimLens Intake API",
    version="0.1.0",
)

app.include_router(router, prefix="/intake")


@app.get("/health")
def health():
    return {"status": "ok"}