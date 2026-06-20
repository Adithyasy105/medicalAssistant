from fastapi import APIRouter, UploadFile, File
from typing import List
from modules.load_vectorstore import load_vectorstore
from fastapi.responses import JSONResponse
from logger import logger


router=APIRouter()

@router.post("/upload_pdfs/")
async def upload_pdfs(files:List[UploadFile] = File(...)):
    try:
        logger.info("Recieved uploaded files")
        load_vectorstore(files)
        logger.info("Document added to vectorstore")
        return {"messages":"Files processed and vectorstore updated"}
    except ValueError as ve:
        if str(ve) == "NON_MEDICAL_DOCUMENT":
            logger.warning("Upload rejected: Non-medical document detected.")
            return JSONResponse(status_code=400, content={"error": "Upload Rejected: This does not appear to be a clinical or medical document."})
        return JSONResponse(status_code=500, content={"error": str(ve)})
    except Exception as e:
        logger.exception("Error during PDF upload")
        error_msg = str(e)
        if "429" in error_msg or "Quota exceeded" in error_msg:
            error_msg = "Google API Rate Limit Exceeded (15 RPM). Please wait 60 seconds."
        return JSONResponse(status_code=500,content={"error": error_msg})