import { useState } from "react";
import "./App.css";
import pinkBot from "./assets/pink-bot.png";

function App() {
  const [inputText, setInputText] = useState("");
  const [summary, setSummary] = useState("");
  const [pdfFile, setPdfFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [summaryType, setSummaryType] = useState("");

  const handleTextSummarize = async () => {
    if (inputText.trim() === "") {
      alert("Please enter some text first.");
      return;
    }

    try {
      setLoading(true);
      setSummary("");
      setSummaryType("");

      const response = await fetch("https://ai-based-text-summarization-gy2h.onrender.com", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          text: inputText
        })
      });

      const data = await response.json();

      if (data.error) {
        alert(data.error);
        return;
      }

      setSummary(data.summary);
      setSummaryType("Text Summary");
    } catch (error) {
      console.error(error);
      alert("Backend connection failed. Make sure FastAPI is running.");
    } finally {
      setLoading(false);
    }
  };

  const handlePdfSummarize = async () => {
    if (!pdfFile) {
      alert("Please select a PDF file first.");
      return;
    }

    try {
      setLoading(true);
      setSummary("");
      setSummaryType("");

      const formData = new FormData();
      formData.append("file", pdfFile);

      const response = await fetch("https://ai-based-text-summarization-gy2h.onrender.com-pdf", {
        method: "POST",
        body: formData
      });

      const data = await response.json();

      if (data.error) {
        alert(data.error);
        return;
      }

      setSummary(data.summary);
      setSummaryType(`PDF Summary: ${data.filename}`);
    } catch (error) {
      console.error(error);
      alert("PDF summarization failed. Make sure FastAPI is running.");
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setInputText("");
    setPdfFile(null);
    setSummary("");
    setSummaryType("");
  };

  return (
    <div className="app-container">
      <div className="floating-bubbles">
        <span></span>
        <span></span>
        <span></span>
        <span></span>
        <span></span>
        <span></span>
        <span></span>
      </div>

      <div className={`image-bot ${summary ? "happy" : ""}`}>
        <div className="bot-message">
          {summary ? "Summary ready!" : loading ? "Summarizing..." : "I am ready!"}
        </div>

        <img src={pinkBot} alt="Pink AI Bot" />
      </div>

      <div className="card">
        <h1>AI Text Summarization Platform</h1>

        <p className="subtitle">
          Paste text or upload a PDF file to generate a concise AI summary.
        </p>

        <div className="input-section">
          <label className="section-label">Enter Text</label>

          <textarea
            placeholder="Paste your long text here..."
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
          />

          <button onClick={handleTextSummarize} disabled={loading}>
            {loading ? "Generating..." : "Summarize Text"}
          </button>
        </div>

        <div className="divider">
          <span>OR</span>
        </div>

        <div className="pdf-section">
          <label className="section-label">Upload PDF</label>

          <label className="file-upload-box">
            <input
              type="file"
              accept="application/pdf"
              onChange={(e) => setPdfFile(e.target.files[0])}
            />

            <div className="upload-content">
              <div className="upload-icon">📄</div>
              <p>{pdfFile ? pdfFile.name : "Click to choose a PDF file"}</p>
              <small>Only PDF files are supported</small>
            </div>
          </label>

          <button onClick={handlePdfSummarize} disabled={loading}>
            {loading ? "Reading PDF..." : "Summarize PDF"}
          </button>
        </div>

        <button className="clear-btn" onClick={handleClear} disabled={loading}>
          Clear All
        </button>

        {summary && (
          <div className="summary-box">
            <h2>{summaryType}</h2>
            <p>{summary}</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;