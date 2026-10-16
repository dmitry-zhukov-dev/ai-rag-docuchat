from fastapi import FastAPI

app = FastAPI(
    title="DocuChat",
    description="Chat with your own documents",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "docuchat",
    }