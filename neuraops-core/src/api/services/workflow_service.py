"""
Workflow Service - File System Management
CLAUDE.md: Single Responsibility - Workflow filesystem operations
"""

import json
import os
import aiofiles
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import UploadFile, HTTPException

import structlog

from ..models.workflow import WorkflowTemplate, WorkflowInfo, WorkflowStatus
from ..models.responses import APIResponse

logger = structlog.get_logger()


class WorkflowService:
    """Service for workflow filesystem operations."""
    
    # Constants to eliminate S1192 string literal duplication
    JSON_EXTENSION = ".json"
    WORKFLOW_NOT_FOUND_MSG = "Workflow template not found"

    def __init__(self, base_data_dir: str = "/app/data"):
        """Initialize with base data directory."""
        self.base_data_dir = Path(base_data_dir)
        self.workflows_dir = self.base_data_dir / "workflows"
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Ensure workflow directories exist."""
        try:
            self.workflows_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Workflow directories ensured at {self.workflows_dir}")
        except Exception as e:
            logger.error(f"Failed to create workflow directories: {e}")
            raise

    async def get_workflow_templates_from_filesystem(self) -> List[Dict[str, Any]]:
        """
        Scan filesystem for workflow templates.
        
        Returns:
            List of workflow template information
        """
        templates = []
        
        try:
            if not self.workflows_dir.exists():
                logger.info("Workflows directory does not exist, returning empty list")
                return templates

            # Scan for JSON workflow files
            for workflow_file in self.workflows_dir.rglob("*.json"):
                try:
                    relative_path = workflow_file.relative_to(self.workflows_dir)
                    section_parts = relative_path.parts[:-1]  # All parts except filename
                    section_id = "/".join(section_parts) if section_parts else "root"
                    
                    # Get file stats
                    stat = workflow_file.stat()
                    
                    # Try to read and parse workflow content
                    async with aiofiles.open(workflow_file, 'r', encoding='utf-8') as f:
                        content = await f.read()
                        workflow_data = json.loads(content)
                    
                    template_info = {
                        "file_name": workflow_file.name,
                        "file_path": str(relative_path),
                        "section_id": section_id,
                        "content": content,
                        "size": stat.st_size,
                        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "extension": workflow_file.suffix,
                        "workflow_name": workflow_data.get("name", workflow_file.stem),
                        "workflow_description": workflow_data.get("description", ""),
                        "workflow_version": workflow_data.get("version", "1.0.0"),
                        "steps_count": len(workflow_data.get("steps", []))
                    }
                    
                    templates.append(template_info)
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON in workflow file {workflow_file}: {e}")
                    continue
                except Exception as e:
                    logger.warning(f"Error processing workflow file {workflow_file}: {e}")
                    continue

            logger.info(f"Found {len(templates)} workflow templates in filesystem")
            return sorted(templates, key=lambda x: x["modified"], reverse=True)

        except Exception as e:
            logger.error(f"Error scanning workflow templates: {e}")
            raise HTTPException(status_code=500, detail="Failed to scan workflow templates")

    async def upload_workflow_template(self, section_id: str, filename: str, file: UploadFile) -> Dict[str, Any]:
        """
        Upload a workflow template file.
        
        Args:
            section_id: Section identifier for organization
            filename: Desired filename
            file: Uploaded file
            
        Returns:
            Upload result information
        """
        try:
            # Create section directory
            section_dir = self.workflows_dir / section_id
            section_dir.mkdir(parents=True, exist_ok=True)
            
            # Ensure filename has .json extension
            if not filename.endswith(self.JSON_EXTENSION):
                filename += self.JSON_EXTENSION
            
            file_path = section_dir / filename
            
            # Read and validate JSON content
            content = await file.read()
            try:
                workflow_data = json.loads(content.decode('utf-8'))
                # Basic validation
                if not isinstance(workflow_data, dict):
                    raise ValueError("Workflow must be a JSON object")
                if "name" not in workflow_data:
                    workflow_data["name"] = filename.replace(self.JSON_EXTENSION, '')
                if "version" not in workflow_data:
                    workflow_data["version"] = "1.0.0"
                if "steps" not in workflow_data:
                    workflow_data["steps"] = []
                
                # Re-encode with proper formatting
                formatted_content = json.dumps(workflow_data, indent=2, ensure_ascii=False)
                
            except json.JSONDecodeError as e:
                raise HTTPException(status_code=400, detail=f"Invalid workflow JSON: {str(e)}")
            
            # Write file
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(formatted_content)
            
            logger.info(f"Workflow template uploaded: {file_path}")
            
            return {
                "filename": filename,
                "section_id": section_id,
                "size": len(formatted_content.encode('utf-8')),
                "path": str(file_path.relative_to(self.workflows_dir))
            }
            
        except Exception as e:
            logger.error(f"Failed to upload workflow template: {e}")
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(status_code=500, detail="Failed to upload workflow template")

    def delete_workflow_template(self, section_id: str, filename: str) -> bool:
        """
        Delete a workflow template file.
        
        Args:
            section_id: Section identifier
            filename: Filename to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            file_path = self.workflows_dir / section_id / filename
            
            if not file_path.exists():
                raise HTTPException(status_code=404, detail=self.WORKFLOW_NOT_FOUND_MSG)
            
            file_path.unlink()
            logger.info(f"Workflow template deleted: {file_path}")
            
            # Clean up empty directories
            try:
                if file_path.parent != self.workflows_dir and not any(file_path.parent.iterdir()):
                    file_path.parent.rmdir()
            except OSError:
                pass  # Ignore cleanup errors
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete workflow template: {e}")
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(status_code=500, detail="Failed to delete workflow template")

    async def get_workflow_template_content(self, section_id: str, filename: str) -> Dict[str, Any]:
        """
        Get workflow template content.
        
        Args:
            section_id: Section identifier
            filename: Filename to read
            
        Returns:
            Template content and metadata
        """
        try:
            file_path = self.workflows_dir / section_id / filename
            
            if not file_path.exists():
                raise HTTPException(status_code=404, detail=self.WORKFLOW_NOT_FOUND_MSG)
            
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            # Parse and validate JSON
            try:
                workflow_data = json.loads(content)
            except json.JSONDecodeError as e:
                raise HTTPException(status_code=400, detail=f"Invalid JSON in workflow template: {str(e)}")
            
            return {
                "content": content,
                "parsed_data": workflow_data,
                "filename": filename,
                "section_id": section_id
            }
            
        except Exception as e:
            logger.error(f"Failed to get workflow template content: {e}")
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(status_code=500, detail="Failed to get workflow template content")

    async def update_workflow_template_content(self, section_id: str, filename: str, content: str) -> Dict[str, Any]:
        """
        Update workflow template content.
        
        Args:
            section_id: Section identifier
            filename: Filename to update
            content: New content
            
        Returns:
            Update result information
        """
        try:
            file_path = self.workflows_dir / section_id / filename
            
            if not file_path.exists():
                raise HTTPException(status_code=404, detail=self.WORKFLOW_NOT_FOUND_MSG)
            
            # Validate JSON content
            try:
                workflow_data = json.loads(content)
                # Basic validation and formatting
                if not isinstance(workflow_data, dict):
                    raise ValueError("Workflow must be a JSON object")
                
                # Ensure required fields
                if "name" not in workflow_data:
                    workflow_data["name"] = filename.replace(self.JSON_EXTENSION, '')
                if "version" not in workflow_data:
                    workflow_data["version"] = "1.0.0"
                if "steps" not in workflow_data:
                    workflow_data["steps"] = []
                
                # Update timestamp
                workflow_data["updated_at"] = datetime.now(timezone.utc).isoformat()
                
                # Format JSON nicely
                formatted_content = json.dumps(workflow_data, indent=2, ensure_ascii=False)
                
            except json.JSONDecodeError as e:
                raise HTTPException(status_code=400, detail=f"Invalid workflow JSON: {str(e)}")
            
            # Write updated content
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(formatted_content)
            
            logger.info(f"Workflow template updated: {file_path}")
            
            return {
                "filename": filename,
                "section_id": section_id,
                "size": len(formatted_content.encode('utf-8')),
                "updated_at": workflow_data["updated_at"]
            }
            
        except Exception as e:
            logger.error(f"Failed to update workflow template content: {e}")
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(status_code=500, detail="Failed to update workflow template content")

    async def create_sample_workflows(self) -> None:
        """Create sample workflow templates for demo purposes."""
        sample_workflows = [
            {
                "filename": "deploy-webapp.json",
                "section": "deployment",
                "content": {
                    "name": "Deploy Web Application",
                    "description": "Deploy a web application with health checks",
                    "version": "1.0.0",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "steps": [
                        {
                            "step_id": "build",
                            "name": "Build Application",
                            "type": "command",
                            "command": "docker build -t myapp:latest .",
                            "timeout": 300
                        },
                        {
                            "step_id": "deploy",
                            "name": "Deploy to Production",
                            "type": "deployment",
                            "target": "production",
                            "rollback_on_failure": True
                        },
                        {
                            "step_id": "health_check",
                            "name": "Health Check",
                            "type": "validation",
                            "endpoint": "/health",
                            "expected_status": 200
                        }
                    ]
                }
            },
            {
                "filename": "backup-database.json",
                "section": "maintenance",
                "content": {
                    "name": "Database Backup",
                    "description": "Automated database backup workflow",
                    "version": "1.0.0",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "steps": [
                        {
                            "step_id": "pre_backup",
                            "name": "Pre-backup validation",
                            "type": "validation",
                            "check": "disk_space"
                        },
                        {
                            "step_id": "backup",
                            "name": "Create backup",
                            "type": "command",
                            "command": "pg_dump -U postgres mydb > backup.sql"
                        },
                        {
                            "step_id": "upload",
                            "name": "Upload to S3",
                            "type": "storage",
                            "destination": "s3://backups/"
                        }
                    ]
                }
            }
        ]
        
        for sample in sample_workflows:
            try:
                section_dir = self.workflows_dir / sample["section"]
                section_dir.mkdir(parents=True, exist_ok=True)
                
                file_path = section_dir / sample["filename"]
                if not file_path.exists():
                    content = json.dumps(sample["content"], indent=2, ensure_ascii=False)
                    async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                        await f.write(content)
                    logger.info(f"Created sample workflow: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to create sample workflow {sample['filename']}: {e}")


# Global service instance
workflow_service = WorkflowService()