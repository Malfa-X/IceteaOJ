from fastapi import FastAPI


app = FastAPI(
    title="Mini OJ",
    version="0.1.0",
)


@app.get("/api/health")
async def health_check() -> dict:
    return {
        "code": 200,
        "msg": "success",
        "data": {
            "status": "ok",
        },
    }