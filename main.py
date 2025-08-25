from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
import base64
from typing import List, Optional
import tempfile
import shutil
from pathlib import Path
from pydantic import BaseModel
import logging

# Import your existing functionality
from unstructured.partition.pdf import partition_pdf
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.vectorstores import Chroma
from langchain.storage import InMemoryStore
from langchain.schema.document import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.retrievers.multi_vector import MultiVectorRetriever
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ChatWithPDF API",
    description="API for processing PDFs and answering questions using RAG",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables to store the retriever and processed data
retriever = None
processed_files = {}

class PDFResponse(BaseModel):
    message: str
    file_id: str
    chunks_count: int
    images_count: int
    tables_count: int

class QueryResponse(BaseModel):
    answer: str
    sources: List[str]
    confidence: float

@app.get("/")
async def root():
    return {"message": "ChatWithPDF API is running!"}

@app.post("/upload-pdf", response_model=PDFResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """Upload and process a PDF file"""
    global retriever, processed_files
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        shutil.copyfileobj(file.file, tmp_file)
        tmp_path = tmp_file.name
    
    try:
        # Create output directory
        output_path = "output"
        os.makedirs(output_path, exist_ok=True)
        
        # Process PDF
        chunks = partition_pdf(
            filename=tmp_path,
            infer_table_structure=True,
            strategy="hi_res",
            extract_image_block_types=["Image"],
            image_output_dir_path=output_path,
            extract_image_block_to_payload=True,
            chunking_strategy="by_title",
            max_characters=10000,
            combine_text_under_n_chars=2000,
            new_after_n_chars=6000,
        )
        
        # Separate tables from texts
        tables = []
        texts = []
        images = []
        for chunk in chunks:
            if "Table" in str(type(chunk)):
                tables.append(chunk)
            elif "Image" in str(type(chunk)):
                images.append(chunk)
            else:
                texts.append(chunk)
        
        logger.info(f"Processed PDF: {len(texts)} texts, {len(tables)} tables, {len(images)} images")
        
        # Check if we have content to process
        if not texts and not tables and not images:
            raise HTTPException(status_code=400, detail="No content could be extracted from the PDF")
        
        # Initialize Groq model
        try:
            model = ChatGroq(temperature=0.3, model="deepseek-r1-distill-llama-70b")
        except Exception as e:
            logger.error(f"Failed to initialize Groq model: {e}")
            # Fallback to a simpler approach
            model = None
        
        # Summarize text and tables if model is available
        text_summaries = []
        table_summaries = []
        image_summaries = []
        
        if model:
            try:
                # Text summarization
                prompt_text = """You are a financial analyst reviewing a company's annual report. 
                Summarize the following section clearly, focusing on key financial metrics, 
                management discussion, risks, opportunities, and business outlook. 
                Avoid generic summaries, highlight insights useful for investors and stakeholders. 

                Section:
                {element}

                Analyst Summary:"""
                prompt = ChatPromptTemplate.from_template(prompt_text)
                summarize_chain = {"element": lambda x: x} | prompt | model | StrOutputParser()
                
                # Summarize texts
                if texts:
                    text_summaries = summarize_chain.batch(texts, {"max_concurrency": 3})
                    logger.info(f"Generated {len(text_summaries)} text summaries")
                
                # Summarize tables
                if tables:
                    tables_html = [table.metadata.text_as_html for table in tables]
                    table_summaries = summarize_chain.batch(tables_html, {"max_concurrency": 3})
                    logger.info(f"Generated {len(table_summaries)} table summaries")
                
                # Simple image descriptions (no complex image processing)
                if images:
                    image_summaries = [f"Image {i+1}: Contains visual content from the document" for i in range(len(images))]
                    logger.info(f"Generated {len(image_summaries)} image descriptions")
                    
            except Exception as e:
                logger.error(f"Error during summarization: {e}")
                # Fallback to simple summaries
                text_summaries = [str(text)[:500] for text in texts]
                table_summaries = [f"Table {i+1}: {str(table)[:500]}" for i, table in enumerate(tables)]
                image_summaries = [f"Image {i+1}: Visual content" for i in range(len(images))]
        else:
            # Simple fallback summaries
            text_summaries = [str(text)[:500] for text in texts]
            table_summaries = [f"Table {i+1}: {str(table)[:500]}" for i, table in enumerate(tables)]
            image_summaries = [f"Image {i+1}: Visual content" for i in range(len(images))]
        
        # Setup vector store with fallback embeddings
        try:
            embedding_model = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        except Exception as e:
            logger.error(f"Failed to initialize Google embeddings: {e}")
            # Use a simple text-based approach instead
            embedding_model = None
        
        if embedding_model:
            try:
                vectorstore = Chroma(
                    collection_name="multi_modal_rag",
                    embedding_function=embedding_model
                )
                store = InMemoryStore()
                id_key = "doc_id"
                
                retriever = MultiVectorRetriever(
                    vectorstore=vectorstore,
                    docstore=store,
                    id_key=id_key,
                )
                
                # Add documents to vector store
                def safe_add_to_vectorstore(retriever, docs, raw_items, id_key):
                    filtered_docs = [doc for doc in docs if doc.page_content.strip()]
                    if filtered_docs:
                        retriever.vectorstore.add_documents(filtered_docs)
                        retriever.docstore.mset(list(zip([doc.metadata[id_key] for doc in filtered_docs], raw_items)))
                        return len(filtered_docs)
                    return 0
                
                # Add texts
                doc_ids = [str(uuid.uuid4()) for _ in texts]
                summary_texts = [
                    Document(page_content=summary, metadata={id_key: doc_ids[i]})
                    for i, summary in enumerate(text_summaries)
                ]
                texts_added = safe_add_to_vectorstore(retriever, summary_texts, texts, id_key)
                
                # Add tables
                table_ids = [str(uuid.uuid4()) for _ in tables]
                summary_tables = [
                    Document(page_content=summary, metadata={id_key: table_ids[i]})
                    for i, summary in enumerate(table_summaries)
                ]
                tables_added = safe_add_to_vectorstore(retriever, summary_tables, tables, id_key)
                
                # Add image summaries
                img_ids = [str(uuid.uuid4()) for _ in images]
                summary_img = [
                    Document(page_content=summary, metadata={id_key: img_ids[i]})
                    for i, summary in enumerate(image_summaries)
                ]
                images_added = safe_add_to_vectorstore(retriever, summary_img, images, id_key)
                
                logger.info(f"Successfully added to vector store: {texts_added} texts, {tables_added} tables, {images_added} images")
                
            except Exception as e:
                logger.error(f"Error setting up vector store: {e}")
                retriever = None
                texts_added = len(texts)
                tables_added = len(tables)
                images_added = len(images)
        else:
            # Fallback: store summaries in memory
            retriever = None
            texts_added = len(texts)
            tables_added = len(tables)
            images_added = len(images)
            logger.info("Using fallback storage method")
        
        # Store processed data
        file_id = str(uuid.uuid4())
        processed_files[file_id] = {
            "chunks": len(chunks),
            "texts": texts_added,
            "tables": tables_added,
            "images": images_added,
            "output_path": output_path,
            "text_summaries": text_summaries,
            "table_summaries": table_summaries,
            "image_summaries": image_summaries
        }
        
        return PDFResponse(
            message="PDF processed successfully",
            file_id=file_id,
            chunks_count=len(chunks),
            images_count=len(images),
            tables_count=len(tables)
        )
        
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")
    finally:
        # Clean up temporary file
        os.unlink(tmp_path)

@app.post("/ask", response_model=QueryResponse)
async def ask_question(question: str = Form(...)):
    """Ask a question about the processed PDF"""
    global retriever, processed_files
    
    logger.info(f"Received question: {question}")
    
    if not processed_files:
        logger.warning("No PDF has been processed yet")
        raise HTTPException(status_code=400, detail="No PDF has been processed yet. Please upload a PDF first.")
    
    try:
        # Get the most recent processed file
        latest_file_id = list(processed_files.keys())[-1]
        file_data = processed_files[latest_file_id]
        
        logger.info(f"Using file data: {file_data}")
        
        # If we have a retriever, use it
        if retriever is not None:
            logger.info("Using retriever to find relevant documents")
            try:
                docs = retriever.invoke(question)
                logger.info(f"Retrieved {len(docs) if docs else 0} documents")
                
                if not docs:
                    return QueryResponse(
                        answer="I couldn't find any relevant information to answer your question.",
                        sources=[],
                        confidence=0.0
                    )
                
                # Extract text content from documents
                sources = []
                for doc in docs:
                    if hasattr(doc, 'page_content'):
                        sources.append(doc.page_content)
                    elif hasattr(doc, 'text'):
                        sources.append(doc.text)
                
                logger.info(f"Extracted {len(sources)} sources")
                
            except Exception as e:
                logger.error(f"Error using retriever: {e}")
                sources = []
        else:
            # Fallback: use stored summaries
            logger.info("Using fallback method with stored summaries")
            sources = []
            if file_data.get('text_summaries'):
                sources.extend(file_data['text_summaries'])
            if file_data.get('table_summaries'):
                sources.extend(file_data['table_summaries'])
            if file_data.get('image_summaries'):
                sources.extend(file_data['image_summaries'])
            
            logger.info(f"Using {len(sources)} stored summaries as sources")
        
        if not sources:
            return QueryResponse(
                answer="I couldn't find any relevant information to answer your question.",
                sources=[],
                confidence=0.0
            )
        
        # Create a summary answer
        answer_prompt = f"""
        You are an AI financial analyst specializing in company annual reports. 
        Use the following extracted sections to answer the user's question. 
        Be factual, analytical, and provide insights as if you are guiding an investor or stakeholder. 
        If financial metrics or strategic direction are mentioned, highlight them. 
        Avoid speculation beyond the provided content.

        Question: {question}

        Annual Report Insights:
        {' '.join(sources[:3])}

        Final Answer (Analyst Perspective):
        """
        
        logger.info("Generating answer using Groq")
        
        # Get answer from Groq
        try:
            model = ChatGroq(temperature=0.3, model="deepseek-ai/DeepSeek-R1")
            prompt = ChatPromptTemplate.from_template(answer_prompt)
            chain = prompt | model | StrOutputParser()
            
            answer = chain.invoke({"question": question})
            logger.info("Successfully generated answer")
            
            return QueryResponse(
                answer=answer,
                sources=sources[:3],  # Return first 3 sources
                confidence=0.8  # Placeholder confidence score
            )
            
        except Exception as e:
            logger.error(f"Error generating answer with Groq: {e}")
            # Fallback: create a simple answer from sources
            fallback_answer = f"Based on the available information, I can provide some context about your question '{question}'. The document contains information about: {' '.join(sources[:2])}"
            
            return QueryResponse(
                answer=fallback_answer,
                sources=sources[:3],
                confidence=0.5
            )
        
    except Exception as e:
        logger.error(f"Error in ask_question: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

@app.get("/files")
async def list_processed_files():
    """List all processed files"""
    return {"files": list(processed_files.keys())}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "retriever_available": retriever is not None}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
