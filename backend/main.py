from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

import fitz  # PyMuPDF
import pdfplumber
import tempfile
import os
import requests

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Later replace with your Vercel frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lighter summarization model for deployment
HF_API_URL = "https://api-inference.huggingface.co/models/sshleifer/distilbart-cnn-12-6"


class InputText(BaseModel):
    text: str


def clean_text(text):
    text = text.replace("\n", " ")
    text = " ".join(text.split())
    return text


def summarize_text(text):
    text = clean_text(text)

    if len(text.split()) < 30:
        return "Please provide at least 30 words for summarization."

    hf_token = os.getenv("HF_TOKEN")

    if not hf_token:
        return "HF_TOKEN is missing on server. Please add it in Render environment variables."

    headers = {
        "Authorization": f"Bearer {hf_token}",
        "Content-Type": "application/json"
    }

    # Keep input small for faster API response
    text = text[:2000]

    payload = {
        "inputs": text,
        "parameters": {
            "max_length": 100,
            "min_length": 25,
            "do_sample": False
        },
        "options": {
            "wait_for_model": True
        }
    }

    try:
        response = requests.post(
            HF_API_URL,
            headers=headers,
            json=payload,
            timeout=90
        )

        try:
            result = response.json()
        except Exception:
            return f"AI API returned non-JSON response: {response.text}"

        if response.status_code != 200:
            return f"AI API error: {result}"

        if isinstance(result, list) and len(result) > 0 and "summary_text" in result[0]:
            return result[0]["summary_text"]

        return f"Unexpected AI response: {result}"

    except requests.exceptions.Timeout:
        return "AI API request timed out. Please try again after a few seconds."

    except Exception as e:
        return f"AI API error: {str(e)}"


def extract_text_with_pymupdf(pdf_path):
    text = ""

    try:
        document = fitz.open(pdf_path)

        for page in document:
            text += page.get_text()

        document.close()

    except Exception as e:
        print("PyMuPDF extraction failed:", e)

    return clean_text(text)


def extract_text_with_pdfplumber(pdf_path):
    text = ""

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()

                if page_text:
                    text += page_text + " "

    except Exception as e:
        print("pdfplumber extraction failed:", e)

    return clean_text(text)


@app.get("/")
def home():
    return {"message": "AI Text Summarization Backend Running"}


@app.post("/summarize")
def summarize(data: InputText):
    text = data.text.strip()

    if not text:
        return {"error": "Text is required"}

    summary = summarize_text(text)

    return {
        "original_length": len(text),
        "summary": summary
    }


@app.post("/summarize-pdf")
async def summarize_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        return {"error": "Only PDF files are allowed"}

    temp_file_path = ""

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(await file.read())
            temp_file_path = temp_file.name

        extracted_text = extract_text_with_pymupdf(temp_file_path)

        if len(extracted_text.split()) < 30:
            extracted_text = extract_text_with_pdfplumber(temp_file_path)

        if len(extracted_text.split()) < 30:
            return {
                "error": "Could not extract enough readable text from this PDF."
            }

        summary = summarize_text(extracted_text)

        return {
            "filename": file.filename,
            "extracted_words": len(extracted_text.split()),
            "summary": summary
        }

    except Exception as e:
        return {"error": str(e)}

    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)