from fastapi import FastAPI
from app.api.routes import router
app=FastAPI(
    title="Smart Trafic Survelliance System",
    description="Backend APIs for ANPR System",
    version="1.0.0"
)

app.include_router(router)

@app.get("/")
def home():
    return {
        "message": "Smart Traffic Surveillance System API is running"
    }