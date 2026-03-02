from fastapi import FastAPI

app = FastAPI(title="Transactions API")

@app.get("/health")
async def health():
    return {"status": "ok"}