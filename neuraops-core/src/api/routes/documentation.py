"""
Documentation API Routes
JWT-authenticated endpoints for documentation system
"""

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from typing import List, Dict, Any
from ..models.documentation import (
    DocSection, 
    DocTemplate, 
    DocQuickLink, 
    DocumentationResponse
)
from ..models.responses import APIResponse
from ..services.documentation_service import DocumentationService
from .auth import get_current_user
from .auth import UserInfo

router = APIRouter(prefix="/documentation", tags=["Documentation"])

# Initialize documentation service
doc_service = DocumentationService()


@router.get("/sections", response_model=APIResponse[List[DocSection]])
async def get_documentation_sections():
    """Get all documentation sections with templates"""
    try:
        sections = await doc_service.load_sections()
        return APIResponse(
            status="success",
            message=f"Retrieved {len(sections)} documentation sections",
            data=sections
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load sections: {str(e)}")


@router.get("/quick-links", response_model=APIResponse[List[DocQuickLink]])
async def get_quick_links():
    """Get quick access links for documentation"""
    try:
        links = await doc_service.load_quick_links()
        return APIResponse(
            status="success",
            message=f"Retrieved {len(links)} quick links",
            data=links
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load quick links: {str(e)}")


@router.get("/template/{template_id}", response_model=APIResponse[DocTemplate])
async def get_template_by_id(template_id: str):
    """Get specific template by ID"""
    try:
        template = await doc_service.get_template_by_id(template_id)
        if not template:
            raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")
        
        return APIResponse(
            status="success",
            message=f"Retrieved template '{template_id}'",
            data=template
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load template: {str(e)}")


@router.get("/section/{section_id}/templates", response_model=APIResponse[List[DocTemplate]])
async def get_templates_by_section(section_id: str):
    """Get all templates in a specific section"""
    try:
        templates = await doc_service.get_templates_by_section(section_id)
        return APIResponse(
            status="success",
            message=f"Retrieved {len(templates)} templates for section '{section_id}'",
            data=templates
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load section templates: {str(e)}")


@router.get("/complete", response_model=APIResponse[DocumentationResponse])
async def get_complete_documentation():
    """Get complete documentation data (sections + quick links)"""
    try:
        documentation = await doc_service.get_complete_documentation()
        return APIResponse(
            status="success",
            message=f"Retrieved complete documentation ({documentation.total_sections} sections, {documentation.total_templates} templates)",
            data=documentation
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load documentation: {str(e)}")


@router.get("/debug")
async def debug_documentation():
    """Debug endpoint to check raw documentation data"""
    try:
        sections = await doc_service.load_sections()
        debug_info = {
            "sections_count": len(sections),
            "sections": []
        }
        
        for section in sections:
            section_debug = {
                "id": section.id,
                "title": section.title,
                "templates_count": len(section.templates),
                "templates": []
            }
            
            for template in section.templates:
                template_debug = {
                    "id": template.id,
                    "name": template.name,
                    "type": template.type,
                    "code_length": len(template.code) if template.code else 0,
                    "has_code": bool(template.code),
                    "file_path": template.file_path
                }
                section_debug["templates"].append(template_debug)
            
            debug_info["sections"].append(section_debug)
        
        return debug_info
    except Exception as e:
        return {"error": str(e), "type": type(e).__name__}

@router.get("/health")
async def documentation_health_check():
    """Check documentation service health"""
    try:
        health_info = doc_service.health_check()
        return APIResponse(
            status="success",
            message="Documentation service is healthy",
            data=health_info
        )
    except Exception as e:
        return APIResponse(
            status="error",
            message=f"Documentation service health check failed: {str(e)}",
            data=None
        )

@router.get("/templates/filesystem", response_model=APIResponse[List[Dict[str, Any]]])
async def get_templates_from_filesystem():
    """Get all templates by scanning filesystem directly"""
    try:
        templates = await doc_service.get_templates_from_filesystem()
        return APIResponse(
            status="success",
            message=f"Retrieved {len(templates)} templates from filesystem",
            data=templates
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to scan templates: {str(e)}")

@router.post("/templates/upload")
async def upload_template(
    section_id: str = Form(...),
    filename: str = Form(...),
    file: UploadFile = File(...)
):
    """Upload a new template file"""
    try:
        # Read file content
        content = await file.read()
        content_str = content.decode('utf-8')
        
        # Use provided filename or file's original name
        final_filename = filename if filename else file.filename
        
        result = await doc_service.upload_template(section_id, final_filename, content_str)
        
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])
        
        return APIResponse(
            status="success",
            message=result["message"],
            data=result
        )
        
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be a text file")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.delete("/templates/{section_id}/{filename}")
async def delete_template(section_id: str, filename: str):
    """Delete a template file"""
    try:
        result = await doc_service.delete_template(section_id, filename)
        
        if result["status"] == "error":
            raise HTTPException(status_code=404, detail=result["message"])
        
        return APIResponse(
            status="success",
            message=result["message"],
            data=result
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")

@router.get("/templates/{section_id}/{filename}/content")
async def get_template_content(section_id: str, filename: str):
    """Get raw content of a template file"""
    try:
        content = await doc_service.get_template_content(section_id, filename)
        
        if content is None:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return APIResponse(
            status="success",
            message="Template content retrieved",
            data={"content": content, "section_id": section_id, "filename": filename}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get template content: {str(e)}")

@router.put("/templates/{section_id}/{filename}")
async def update_template(
    section_id: str,
    filename: str,
    file: UploadFile = File(...)
):
    """Update existing template file"""
    try:
        # Read file content
        content = await file.read()
        content_str = content.decode('utf-8')
        
        result = await doc_service.update_template(section_id, filename, content_str)
        
        if result["status"] == "error":
            raise HTTPException(status_code=404, detail=result["message"])
        
        return APIResponse(
            status="success",
            message=result["message"],
            data=result
        )
        
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be a text file")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")

@router.put("/templates/{section_id}/{filename}/content")
async def update_template_content(
    section_id: str,
    filename: str,
    content: Dict[str, str]
):
    """Update template content via JSON payload"""
    try:
        result = await doc_service.update_template(section_id, filename, content["content"])
        
        if result["status"] == "error":
            raise HTTPException(status_code=404, detail=result["message"])
        
        return APIResponse(
            status="success",
            message=result["message"],
            data=result
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")

@router.get("/templates/all")
async def get_all_templates():
    """Get all templates with their metadata"""
    try:
        templates = await doc_service.get_all_templates()
        filesystem_templates = await doc_service.get_templates_from_filesystem()
        
        return APIResponse(
            status="success",
            message=f"Retrieved {len(templates)} configured templates and {len(filesystem_templates)} filesystem templates",
            data={
                "configured_templates": [template.dict() for template in templates],
                "filesystem_templates": filesystem_templates,
                "total_configured": len(templates),
                "total_filesystem": len(filesystem_templates)
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get templates: {str(e)}")
