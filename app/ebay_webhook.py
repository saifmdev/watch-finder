# app/ebay_webhook.py
from fastapi import FastAPI, Request
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

@app.get("/")
def health_check():
    return {"status": "ok"}

@app.post("/ebay/deletion-notification")
async def ebay_deletion_notification(request: Request):
    payload = await request.json()
    # log or handle the payload
    print("Received deletion notification:", payload)
    return {"received": True}
