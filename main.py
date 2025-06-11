from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import JSONResponse
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, date
import threading
import logging
from services import (
    create_complaint, get_complaint_by_id, get_complaints_by_date,
    update_complaint, delete_complaint, delete_complaint_media,
    upload_file_thread
)

app = FastAPI(title="Rail Sathi Complaint API", version="1.0.0")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date

class RailSathiComplainMediaResponse(BaseModel):
    id: int
    media_type: Optional[str]
    media_url: Optional[str]
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    updated_by: Optional[str]

# Separate the complaint data model
class RailSathiComplainData(BaseModel):
    complain_id: int
    pnr_number: Optional[str]
    is_pnr_validated: Optional[str]
    name: Optional[str]
    mobile_number: Optional[str]
    complain_type: Optional[str]
    complain_description: Optional[str]
    complain_date: Optional[date]
    complain_status: str
    train_id: Optional[int]
    train_number: Optional[str]
    train_name: Optional[str]
    coach: Optional[str]
    berth_no: Optional[int]
    created_at: datetime
    created_by: Optional[str]
    updated_at: datetime
    updated_by: Optional[str]
    # Add the missing fields from your actual data
    train_no: Optional[int]
    train_depot: Optional[str]
    rail_sathi_complain_media_files: List[RailSathiComplainMediaResponse]

# Response wrapper that matches your actual API response structure
class RailSathiComplainResponse(BaseModel):
    message: str
    data: RailSathiComplainData

# Alternative: If you want to keep the flat structure, modify your endpoint to return:
class RailSathiComplainFlatResponse(BaseModel):
    message: str
    complain_id: int
    pnr_number: Optional[str]
    is_pnr_validated: Optional[str]
    name: Optional[str]
    mobile_number: Optional[str]
    complain_type: Optional[str]
    complain_description: Optional[str]
    complain_date: Optional[date]
    complain_status: str
    train_id: Optional[int]
    train_number: Optional[str]
    train_name: Optional[str]
    coach: Optional[str]
    berth_no: Optional[int]
    created_at: datetime
    created_by: Optional[str]
    updated_at: datetime
    updated_by: Optional[str]
    rail_sathi_complain_media_files: List[RailSathiComplainMediaResponse]

@app.get("/complaint/get/{complain_id}", response_model=RailSathiComplainResponse)
async def get_complaint(complain_id: int):
    """Get complaint by ID"""
    try:
        complaint = get_complaint_by_id(complain_id)
        if not complaint:
            raise HTTPException(status_code=404, detail="Complaint not found")
        
        # Wrap the complaint in the expected response format
        return RailSathiComplainResponse(
            message="Complaint retrieved successfully",
            data=complaint
        )
    except Exception as e:
        logger.error(f"Error getting complaint {complain_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/complaint/get/date/{date_str}", response_model=List[RailSathiComplainResponse])
async def get_complaints_by_date_endpoint(date_str: str, mobile_number: Optional[str] = None):
    """Get complaints by date and mobile number"""
    try:
        # Validate date format
        try:
            complaint_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
        
        if not mobile_number:
            raise HTTPException(status_code=400, detail="mobile_number parameter is required")
        
        complaints = get_complaints_by_date(complaint_date, mobile_number)
        
        # Wrap each complaint in the expected response format
        response_list = []
        for complaint in complaints:
            response_list.append(RailSathiComplainResponse(
                message="Complaint retrieved successfully",
                data=complaint
            ))
        
        return response_list
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting complaints by date {date_str}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/complaint/add", response_model=RailSathiComplainResponse)
async def create_complaint_endpoint(
    pnr_number: Optional[str] = Form(None),
    is_pnr_validated: Optional[str] = Form("not-attempted"),
    name: Optional[str] = Form(None),
    mobile_number: Optional[str] = Form(None),
    complain_type: Optional[str] = Form(None),
    complain_description: Optional[str] = Form(None),
    complain_date: Optional[str] = Form(None),
    complain_status: str = Form("pending"),
    train_id: Optional[int] = Form(None),
    train_number: Optional[str] = Form(None),
    train_name: Optional[str] = Form(None),
    coach: Optional[str] = Form(None),
    berth_no: Optional[int] = Form(None),
    rail_sathi_complain_media_files: List[UploadFile] = File(default=[])
):
    """Create new complaint"""
    try:
        # Prepare complaint data
        complaint_data = {
            "pnr_number": pnr_number,
            "is_pnr_validated": is_pnr_validated,
            "name": name,
            "mobile_number": mobile_number,
            "complain_type": complain_type,
            "complain_description": complain_description,
            "complain_date": complain_date,
            "complain_status": complain_status,
            "train_id": train_id,
            "train_number": train_number,
            "train_name": train_name,
            "coach": coach,
            "berth_no": berth_no,
            "created_by": name
        }
        
        # Create complaint
        complaint = create_complaint(complaint_data)
        complain_id = complaint["complain_id"]
        
        # Handle file uploads in threads
        threads = []
        for file_obj in rail_sathi_complain_media_files:
            t = threading.Thread(target=upload_file_thread, args=(file_obj, complain_id, name or ''))
            t.start()
            threads.append(t)
        
        # Wait for all threads to complete
        for t in threads:
            t.join()
        
        # Get updated complaint with media files
        updated_complaint = get_complaint_by_id(complain_id)
        
        return {
            "message": "Complaint created successfully",
            "data": updated_complaint
        }

    except Exception as e:
        logger.error(f"Error creating complaint: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.patch("/complaint/update/{complain_id}", response_model=RailSathiComplainResponse)
async def update_complaint_endpoint(
    complain_id: int,
    pnr_number: Optional[str] = Form(None),
    is_pnr_validated: Optional[str] = Form(None),
    name: Optional[str] = Form(None),
    mobile_number: Optional[str] = Form(None),
    complain_type: Optional[str] = Form(None),
    complain_description: Optional[str] = Form(None),
    complain_date: Optional[str] = Form(None),
    complain_status: Optional[str] = Form(None),
    train_id: Optional[int] = Form(None),
    train_number: Optional[str] = Form(None),
    train_name: Optional[str] = Form(None),
    coach: Optional[str] = Form(None),
    berth_no: Optional[int] = Form(None),
    rail_sathi_complain_media_files: List[UploadFile] = File(default=[])
):
    """Update complaint (partial update)"""
    try:
        # Check if complaint exists and validate permissions
        existing_complaint = get_complaint_by_id(complain_id)
        if not existing_complaint:
            raise HTTPException(status_code=404, detail="Complaint not found")
        
        # Check permissions
        if (existing_complaint["created_by"] != name or 
            existing_complaint["complain_status"] == "completed" or 
            existing_complaint["mobile_number"] != mobile_number):
            raise HTTPException(status_code=403, detail="Only user who created the complaint can update it.")
        
        # Prepare update data (only include non-None values)
        update_data = {}
        if pnr_number is not None: update_data["pnr_number"] = pnr_number
        if is_pnr_validated is not None: update_data["is_pnr_validated"] = is_pnr_validated
        if name is not None: update_data["name"] = name
        if mobile_number is not None: update_data["mobile_number"] = mobile_number
        if complain_type is not None: update_data["complain_type"] = complain_type
        if complain_description is not None: update_data["complain_description"] = complain_description
        if complain_date is not None: update_data["complain_date"] = complain_date
        if complain_status is not None: update_data["complain_status"] = complain_status
        if train_id is not None: update_data["train_id"] = train_id
        if train_number is not None: update_data["train_number"] = train_number
        if train_name is not None: update_data["train_name"] = train_name
        if coach is not None: update_data["coach"] = coach
        if berth_no is not None: update_data["berth_no"] = berth_no
        update_data["updated_by"] = name
        
        # Update complaint
        updated_complaint = update_complaint(complain_id, update_data)
        
        # Handle file uploads in threads
        threads = []
        for file_obj in rail_sathi_complain_media_files:
            t = threading.Thread(target=upload_file_thread, args=(file_obj, complain_id, name or ''))
            t.start()
            threads.append(t)
        
        # Wait for all threads to complete
        for t in threads:
            t.join()
        
        # Get final updated complaint
        final_complaint = get_complaint_by_id(complain_id)
        return final_complaint
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating complaint {complain_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.put("/complaint/update/{complain_id}", response_model=RailSathiComplainResponse)
async def replace_complaint_endpoint(
    complain_id: int,
    pnr_number: Optional[str] = Form(None),
    is_pnr_validated: str = Form("not-attempted"),
    name: Optional[str] = Form(None),
    mobile_number: Optional[str] = Form(None),
    complain_type: Optional[str] = Form(None),
    complain_description: Optional[str] = Form(None),
    complain_date: Optional[str] = Form(None),
    complain_status: str = Form("pending"),
    train_id: Optional[int] = Form(None),
    train_number: Optional[str] = Form(None),
    train_name: Optional[str] = Form(None),
    coach: Optional[str] = Form(None),
    berth_no: Optional[int] = Form(None),
    rail_sathi_complain_media_files: List[UploadFile] = File(default=[])
):
    """Replace complaint (full update)"""
    try:
        # Check if complaint exists and validate permissions
        existing_complaint = get_complaint_by_id(complain_id)
        if not existing_complaint:
            raise HTTPException(status_code=404, detail="Complaint not found")
        
        # Check permissions
        if (existing_complaint["created_by"] != name or 
            existing_complaint["complain_status"] == "completed" or 
            existing_complaint["mobile_number"] != mobile_number):
            raise HTTPException(status_code=403, detail="Only user who created the complaint can update it.")
        
        # Prepare full update data
        update_data = {
            "pnr_number": pnr_number,
            "is_pnr_validated": is_pnr_validated,
            "name": name,
            "mobile_number": mobile_number,
            "complain_type": complain_type,
            "complain_description": complain_description,
            "complain_date": complain_date,
            "complain_status": complain_status,
            "train_id": train_id,
            "train_number": train_number,
            "train_name": train_name,
            "coach": coach,
            "berth_no": berth_no,
            "updated_by": name
        }
        
        # Update complaint
        updated_complaint = update_complaint(complain_id, update_data)
        
        # Handle file uploads in threads
        threads = []
        for file_obj in rail_sathi_complain_media_files:
            t = threading.Thread(target=upload_file_thread, args=(file_obj, complain_id, name or ''))
            t.start()
            threads.append(t)
        
        # Wait for all threads to complete
        for t in threads:
            t.join()
        
        # Get final updated complaint
        final_complaint = get_complaint_by_id(complain_id)
        return final_complaint
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error replacing complaint {complain_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/complaint/delete/{complain_id}")
async def delete_complaint_endpoint(
    complain_id: int,
    name: str = Form(...),
    mobile_number: str = Form(...)
):
    """Delete complaint"""
    try:
        # Check if complaint exists and validate permissions
        existing_complaint = get_complaint_by_id(complain_id)
        if not existing_complaint:
            raise HTTPException(status_code=404, detail="Complaint not found")
        
        # Check permissions
        if (existing_complaint["created_by"] != name or 
            existing_complaint["complain_status"] == "completed" or 
            existing_complaint["mobile_number"] != mobile_number):
            raise HTTPException(status_code=403, detail="Only user who created the complaint can delete it.")
        
        # Delete complaint
        delete_complaint(complain_id)
        return {"message": "Complaint deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting complaint {complain_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/media/delete/{complain_id}")
async def delete_complaint_media_endpoint(
    complain_id: int,
    name: str = Form(...),
    mobile_number: str = Form(...),
    deleted_media_ids: List[int] = Form(...)
):
    """Delete complaint media files"""
    try:
        # Check if complaint exists and validate permissions
        existing_complaint = get_complaint_by_id(complain_id)
        if not existing_complaint:
            raise HTTPException(status_code=404, detail="Complaint not found")
        
        # Check permissions
        if (existing_complaint["created_by"] != name or 
            existing_complaint["complain_status"] == "completed" or 
            existing_complaint["mobile_number"] != mobile_number):
            raise HTTPException(status_code=403, detail="Only user who created the complaint can update it.")
        
        if not deleted_media_ids:
            raise HTTPException(status_code=400, detail="No media IDs provided for deletion.")
        
        # Delete media files
        deleted_count = delete_complaint_media(complain_id, deleted_media_ids)
        
        if deleted_count == 0:
            raise HTTPException(status_code=400, detail="No matching media files found for deletion.")
        
        return {"message": f"{deleted_count} media file(s) deleted successfully."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting complaint media {complain_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)