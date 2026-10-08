import asyncio
import os
import json
import sys
import logging
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from supabase import create_client, Client

# ============================================================================
# Configuration & Initialization
# ============================================================================
# Setting up logging to write all logs to one log file
logging.basicConfig(
    filename='rag_api.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

# ============================================================================
# Supabase Client Initialization

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.error("CRITICAL: Missing Supabase credentials in environment variables.")
    raise ValueError("CRITICAL: Missing Supabase credentials in environment variables.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
genai_client = genai.Client()

EMBEDDING_MODEL = "gemini-embedding-001"
GENERATION_MODEL = "gemini-3.5-flash-lite"
DB_TABLE_NAME = "agentic_rag"

# ============================================================================
# FastAPI App Initialization
# ============================================================================
app = FastAPI(
    title="Agentic RAG API",
    description="Query ingested WEO data with AI analysis and chart data",
    version="1.0.0"
)

# ============================================================================
# Pydantic Models
# ============================================================================
class QueryRequest(BaseModel):
    question: str

class ChartDataPoint(BaseModel):
    series: str
    x_axis: str
    y_axis: float

class AnalysisResponse(BaseModel):
    analysis: str
    chart_data: List[ChartDataPoint]

class QueryResponse(BaseModel):
    status: str
    question: str
    response: AnalysisResponse

class ExampleQueriesResponse(BaseModel):
    examples: List[str]

# ============================================================================
# Core RAG Functions
# ============================================================================
def query_weo_database(query: str, match_count: int = 3) -> Dict[str, Any]:
    """Searches the agentic_rag table for macroeconomic data and metrics."""
    logger.info(f"[SEARCH] Vector Search: '{query}'")
    
    response = genai_client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=query,
    )
    query_vector = response.embeddings[0].values

    result = supabase.rpc(
        "match_documents", 
        {
            "query_embedding": query_vector,
            "match_count": match_count
        }
    ).execute()

    if result.data:
        return {
            "retrieved_context": "\n\n".join([doc["content"] for doc in result.data]),
            "raw_documents": result.data
        }
    
    return {
        "retrieved_context": "No macroeconomic data found matching the query.",
        "raw_documents": []
    }

# ============================================================================
# Agentic RAG System
# ============================================================================
weo_analyst_agent = LlmAgent(
    name="macro_analyst",
    model=GENERATION_MODEL,
    description="An autonomous agent specializing in global economic prospects, policies, and commodity metrics.",
    instruction="""
    You are an expert macroeconomic analyst.
    1. Always use the `query_weo_database` tool to fetch exact numbers, percentages, and baseline assumptions before answering.
    2. Rely on the Markdown tables retrieved from the database to provide exact data points. Do not hallucinate statistics.
    3. You MUST output your final response as a pure, valid JSON object. Do not wrap it in markdown code blocks (e.g., do not use ```json).
    
    Use exactly this JSON structure:
    {
      "analysis": "Your detailed text response explaining the trends, citing the exact numbers, and answering the user's question.",
      "chart_data": [
        {
          "series": "Name of the metric (e.g., Fuel Commodity Price Change % or Global GDP Growth %)", 
          "x_axis": "Year (e.g., '2025')", 
          "y_axis": 0.0 
        }
      ]
    }
    """,
    tools=[query_weo_database],
)

async def run_agentic_rag(query: str) -> Dict[str, Any]:
    """Executes the agentic RAG pipeline and returns structured response."""
    logger.info(f"[USER QUERY]: {query}")
    
    runner = InMemoryRunner(agent=weo_analyst_agent)
    session_id = f"weo_analysis_{int(__import__('time').time())}"

    await runner.session_service.create_session(
        app_name=runner.app_name,
        user_id="api_user",
        session_id=session_id,
    )

    response_text = ""
    async for event in runner.run_async(
        user_id="api_user",
        session_id=session_id,
        new_message=types.Content(role="user", parts=[types.Part(text=query)]),
    ):
        if getattr(event, "is_final_response", False) and getattr(event, "content", None):
            response_text = "".join(
                part.text
                for part in event.content.parts
                if getattr(part, "text", None) is not None
            )

    logger.info(f"[RAW RESPONSE]:\n{response_text}")

    # Parse JSON response
    try:
        clean_json_str = response_text.replace("```json", "").replace("```", "").strip()
        parsed_data = json.loads(clean_json_str)
        return {
            "status": "success",
            "data": parsed_data
        }
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {str(e)}")
        return {
            "status": "error",
            "error": "Failed to parse agent response",
            "raw_response": response_text
        }

# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/examples", response_model=ExampleQueriesResponse)
async def get_example_queries() -> ExampleQueriesResponse:
    """Return example questions users can ask the WEO database."""
    return ExampleQueriesResponse(
        examples=[
            "What are the global GDP growth projections for 2025 and 2026?",
            "How do growth forecasts compare between advanced economies and emerging markets?",
            "What are the projected trends in global inflation?",
            "How are energy and food commodity prices expected to change?",
        ]
    )

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Agentic RAG API",
        "version": "1.0.0"
    }

@app.post("/query", response_model=QueryResponse)
async def query_rag(request: QueryRequest):
    """
    Query the WEO database using agentic RAG.
    Returns analysis with chart data.
    """
    try:
        if not request.question or len(request.question.strip()) == 0:
            logger.warning("Query endpoint called with an empty question.")
            raise HTTPException(status_code=400, detail="Question cannot be empty")
        
        logger.info(f"Received query request: {request.question}")
        result = await run_agentic_rag(request.question)
        
        if result["status"] == "error":
            logger.error(f"Agent error in query: {result.get('error', 'Unknown error')}")
            raise HTTPException(
                status_code=500,
                detail=f"Agent error: {result.get('error', 'Unknown error')}"
            )
        
        data = result["data"]
        logger.info("Successfully processed query and returning response.")
        return QueryResponse(
            status="success",
            question=request.question,
            response=AnalysisResponse(
                analysis=data.get("analysis", ""),
                chart_data=[ChartDataPoint(**point) for point in data.get("chart_data", [])]
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query endpoint exception: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Starting Agentic RAG API server...")
    logger.info("📖 API Documentation: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)
