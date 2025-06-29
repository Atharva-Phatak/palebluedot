from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pbd.webhooks.metaflow_webhook.events.metaflow import publish_event
import logging

app = FastAPI()


# Add these to your FastAPI main.py
@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/ready")
async def readiness_check():
    return {"status": "ready"}


@app.post("/argoevent", status_code=200)
async def handle_event(request: Request):
    try:
        body = await request.json()
        logging.info(f"Received event: {body}")
        event_id = publish_event(body)
        return {"status": "ok", "event_id": event_id}
    except Exception as e:
        logging.exception("Error processing Argo Event")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": "error", "message": str(e)},
        )
