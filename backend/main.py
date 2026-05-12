from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import fitz  # PyMuPDF
import pdfplumber
import tempfile
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load AI model
model_name = "t5-small"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)


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

    # Split long text into chunks because T5-small has input limits
    words = text.split()
    chunks = []

    chunk_size = 350
    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)

    summaries = []

    for chunk in chunks[:5]:  # limit to first 5 chunks for speed
        input_text = "summarize: " + chunk

        inputs = tokenizer(
            input_text,
            return_tensors="pt",
            max_length=512,
            truncation=True
        )

        output = model.generate(
            inputs["input_ids"],
            max_length=120,
            min_length=30,
            num_beams=4,
            early_stopping=True
        )

        summary = tokenizer.decode(output[0], skip_special_tokens=True)
        summaries.append(summary)

    final_summary = " ".join(summaries)

    return final_summary


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
    if not file.filename.endswith(".pdf"):
        return {"error": "Only PDF files are allowed"}

    temp_file_path = ""

    try:
        # Save uploaded PDF temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(await file.read())
            temp_file_path = temp_file.name

        # First try PyMuPDF
        extracted_text = extract_text_with_pymupdf(temp_file_path)

        # If PyMuPDF gives weak/no text, try pdfplumber
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