# Annual Report AI Agent

An AI-powered agent that analyzes company annual reports (PDFs) to extract insights, summarize financial data, and answer user queries using natural language.

## 🚀 Features
- Upload annual report PDFs (20–200+ pages supported)
- Extract key financial metrics (Revenue, Net Profit, Liabilities, etc.)
- Summarize sections like MD&A, Risk Factors, and Auditor’s Report
- Ask questions in natural language (e.g., *"What was the net profit in 2023?"*)
- Built with **LangChain**, **Groq LLM**, and **Unstructured PDF parsing**

## 🛠️ Tech Stack
- **Backend:** FastAPI
- **AI/LLM:** LangChain + Groq (DeepSeek / Llama models)
- **PDF Processing:** unstructured + pdfminer
- **Frontend (optional):** Streamlit for UI
- **Deployment:** Local / Cloud-ready

## 📂 Project Structure
```
annual-report-ai-agent/
│── main.py                # FastAPI app
│── agent.py               # LangChain agent logic
│── requirements.txt       # Dependencies
│── sample_reports/        # Example annual reports
│── README.md              # Project documentation
```

## ⚡ Installation & Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/shivam-rawat/annual-report-ai-agent.git
   cd annual-report-ai-agent
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the FastAPI app:
   ```bash
   uvicorn main:app --reload
   ```

5. (Optional) Run the Streamlit UI:
   ```bash
   streamlit run app.py
   ```

## 🎯 Usage
- Upload a company annual report (PDF).
- The agent extracts financial insights.
- Ask queries like:
  - "Summarize the risk factors section"
  - "Compare 2022 and 2023 net profit"
  - "What are the future growth strategies?"

## 🔮 Future Enhancements
- Support for multi-company benchmarking
- Integration with financial APIs (Yahoo Finance, Alpha Vantage)
- Visualization dashboard for trends

## 📜 License
MIT License

---
👨‍💻 Developed by **Shivam Rawat**
