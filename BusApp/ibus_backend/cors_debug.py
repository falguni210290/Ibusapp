from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# ✅ CORS setup at the top — confirmed working
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ✅ allow everything for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/test-cors")
def test_cors():
    return {"message": "CORS is working 🎉"}
