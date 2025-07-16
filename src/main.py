import logging
from dotenv import load_dotenv
from uvicorn import run

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import router

from transformers import BlipProcessor, BlipForConditionalGeneration
from sentence_transformers import SentenceTransformer
import torch


logger = logging.getLogger()

app = FastAPI()

app.include_router(router)

# Allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base").to(device)

    sentence_model = SentenceTransformer('all-MiniLM-L6-v2', device=device)

    # Store in FastAPI app state
    app.state.blip_model = blip_model
    app.state.blip_processor = processor
    app.state.sentence_model = sentence_model
    app.state.device = device

@app.get("/")
def root():
    return {"detail": "Hello World"}


if __name__ == "__main__":
    logger.info("Starting the FastAPI application...")
    load_dotenv()

    # Use uvicorn to run the FastAPI application
    run(app, host="0.0.0.0", port=8000, log_level="info")