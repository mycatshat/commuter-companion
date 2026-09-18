from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import journey, meta, plan

app = FastAPI(
    title="Smart Commuter Companion API",
    description="Backend for the Smart Commuter Companion (Rachel persona, EWL Tampines→Raffles Place).",
    version="0.1.0",
)

# Wide open for hackathon/demo purposes -- a real deployment should restrict
# this to the actual frontend origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(meta.router, prefix="/api")
app.include_router(journey.router, prefix="/api")
app.include_router(plan.router, prefix="/api")


@app.get("/")
async def root():
    return {
        "name": "Smart Commuter Companion API",
        "docs": "/docs",
        "try": "/api/journey?scenario=disruption",
    }
