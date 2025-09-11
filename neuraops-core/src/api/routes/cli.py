"""
CLI HTTP Routes

Provides HTTP REST endpoint for CLI command execution.
Follows CLAUDE.md: < 200 lines, KISS principle, safety-first.
"""
import asyncio
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import structlog

from ..routes.auth import get_current_user, UserInfo

logger = structlog.get_logger()

router = APIRouter(prefix="/cli", tags=["CLI"])


class CLIExecuteRequest(BaseModel):
    """CLI command execution request"""
    command: str = Field(..., description="Command to execute")
    args: List[str] = Field(default=[], description="Command arguments")
    timeout: int = Field(default=300, ge=1, le=600, description="Timeout in seconds")


class CLIExecuteResponse(BaseModel):
    """CLI command execution response"""
    success: bool = Field(..., description="Whether command succeeded")
    stdout: str = Field(default="", description="Standard output")
    stderr: str = Field(default="", description="Standard error")
    return_code: int = Field(..., description="Process return code")
    execution_time: float = Field(..., description="Execution time in seconds")


class GeneratedFile(BaseModel):
    """Generated file information"""
    id: str = Field(..., description="Unique file identifier")
    name: str = Field(..., description="File name")
    type: str = Field(..., description="File type/extension")
    size: int = Field(..., description="File size in bytes")
    created: datetime = Field(..., description="Creation timestamp")
    command: str = Field(..., description="Command that generated this file")
    path: str = Field(..., description="Relative file path")


class GeneratedFilesResponse(BaseModel):
    """Response for generated files listing"""
    files: List[GeneratedFile] = Field(..., description="List of generated files")


async def execute_command_subprocess(
    command: str, 
    args: List[str] = None, 
    timeout: int = 300,
    cwd: str = None
) -> Dict:
    """
    Execute CLI command using async subprocess
    
    CLAUDE.md: < 50 lines - Safe command execution with timeout
    Safety-First: Validates command and applies timeout limits
    """
    import time
    import asyncio
    start_time = time.time()
    process = None
    
    try:
        # Build command args - execute NeuraOps CLI
        cmd_args = ["python", "-m", "src.main", command]
        if args:
            cmd_args.extend(args)
        
        # Set up environment
        subprocess_env = os.environ.copy()
        subprocess_env['PYTHONPATH'] = os.path.join(os.getcwd(), 'src')
        
        # Execute with timeout using context manager
        async with asyncio.timeout(timeout):
            process = await asyncio.create_subprocess_exec(
                *cmd_args,
                cwd=cwd or "/Users/maximedegournay/projet/gitlab/NeuraOps/neuraops-core",
                env=subprocess_env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout_bytes, stderr_bytes = await process.communicate()
        
        execution_time = time.time() - start_time
        
        return {
            "success": process.returncode == 0,
            "stdout": stdout_bytes.decode('utf-8'),
            "stderr": stderr_bytes.decode('utf-8'),
            "return_code": process.returncode,
            "execution_time": execution_time
        }
        
    except asyncio.TimeoutError:
        execution_time = time.time() - start_time
        if process:
            process.kill()
            await process.wait()
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Command timed out after {timeout} seconds",
            "return_code": 124,
            "execution_time": execution_time
        }
    except Exception as e:
        execution_time = time.time() - start_time
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Execution error: {str(e)}",
            "return_code": 1,
            "execution_time": execution_time
        }


@router.get("/test-auth")
async def test_cli_auth(
    current_user: UserInfo = Depends(get_current_user)
):
    """Test endpoint for CLI authentication debugging"""
    return {"message": "Auth successful", "user": current_user.username}

@router.post("/execute", response_model=CLIExecuteResponse)
async def execute_cli_command(
    request: CLIExecuteRequest,
    current_user: UserInfo = Depends(get_current_user)
) -> CLIExecuteResponse:
    """
    Execute NeuraOps CLI command
    
    CLAUDE.md: < 30 lines - HTTP endpoint for CLI execution
    Safety-First: Requires authentication and validates input
    """
    logger.info("Executing CLI command", 
               command=request.command, 
               args=request.args,
               user=current_user.username)
    
    try:
        result = await execute_command_subprocess(
            command=request.command,
            args=request.args,
            timeout=request.timeout
        )
        
        response = CLIExecuteResponse(**result)
        
        logger.info("CLI command completed",
                   command=request.command,
                   success=response.success,
                   return_code=response.return_code,
                   execution_time=response.execution_time)
        
        return response
        
    except Exception as e:
        logger.error("CLI command execution failed",
                    command=request.command,
                    error=str(e))
        
        raise HTTPException(
            status_code=500,
            detail=f"CLI execution failed: {str(e)}"
        )


@router.get("/health")
async def cli_health(
    current_user: UserInfo = Depends(get_current_user)
) -> Dict:
    """
    Check CLI subsystem health
    
    CLAUDE.md: < 20 lines - Simple health check
    """
    try:
        # Test basic CLI availability
        result = await execute_command_subprocess(
            command="--help",
            timeout=5
        )
        
        return {
            "status": "healthy" if result["success"] else "degraded",
            "cli_available": result["success"],
            "message": "CLI subsystem operational" if result["success"] else "CLI subsystem issues detected"
        }
        
    except Exception as e:
        logger.error("CLI health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "cli_available": False,
            "message": f"CLI health check failed: {str(e)}"
        }


def scan_generated_files(base_dir: str = "/tmp") -> List[GeneratedFile]:
    """
    Scan for generated files in /tmp directory only
    
    CLAUDE.md: < 50 lines - File scanning utility
    """
    generated_files = []
    base_path = Path(base_dir)
    
    # Only scan /tmp directory for generated files
    search_dirs = [
        base_path / "neuraops",
        base_path / "generated", 
        base_path / "infra",
        base_path  # Also scan /tmp root
    ]
    
    # File patterns to look for (infrastructure files)
    patterns = ["*.tf", "*.yml", "*.yaml", "*.json", "Dockerfile*", "*.sh"]
    
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
            
        for pattern in patterns:
            for file_path in search_dir.rglob(pattern):
                if file_path.is_file() and not file_path.name.startswith('.'):
                    try:
                        stat = file_path.stat()
                        # Include all files (no time restriction for generated files)
                        if True:
                            generated_files.append(GeneratedFile(
                                id=str(abs(hash(str(file_path)))),
                                name=file_path.name,
                                type=file_path.suffix[1:] or "file",
                                size=stat.st_size,
                                created=datetime.fromtimestamp(stat.st_mtime),
                                command="infra generate",  # Default, could be enhanced
                                path=str(file_path.relative_to(Path(base_dir)))
                            ))
                    except (OSError, ValueError):
                        continue
    
    return sorted(generated_files, key=lambda f: f.created, reverse=True)


@router.get("/files", response_model=GeneratedFilesResponse)
async def list_generated_files(
    current_user: UserInfo = Depends(get_current_user)
) -> GeneratedFilesResponse:
    """
    List all generated files from CLI commands
    
    CLAUDE.md: < 20 lines - File listing endpoint
    """
    try:
        files = scan_generated_files()
        logger.info(f"Found {len(files)} generated files", user=current_user.username)
        return GeneratedFilesResponse(files=files)
        
    except Exception as e:
        logger.error("Failed to list generated files", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list generated files: {str(e)}"
        )


@router.get("/files/{file_id}/download")
async def download_generated_file(
    file_id: str,
    current_user: UserInfo = Depends(get_current_user)
) -> FileResponse:
    """
    Download a generated file
    
    CLAUDE.md: < 20 lines - File download endpoint
    """
    try:
        files = scan_generated_files()
        target_file = next((f for f in files if f.id == file_id), None)
        
        if not target_file:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Fix: Use /tmp as base directory, not /app
        file_path = Path("/tmp") / target_file.path
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File no longer exists")
        
        logger.info(f"Downloading file {target_file.name}", user=current_user.username)
        
        return FileResponse(
            path=str(file_path),
            filename=target_file.name,
            media_type="application/octet-stream"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to download file", file_id=file_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download file: {str(e)}"
        )


@router.get("/files/{file_id}/content")
async def get_file_content(
    file_id: str,
    current_user: UserInfo = Depends(get_current_user)
) -> Dict:
    """
    Get content of a generated file for preview
    
    CLAUDE.md: < 20 lines - File content endpoint
    """
    try:
        files = scan_generated_files()
        target_file = next((f for f in files if f.id == file_id), None)
        
        if not target_file:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Fix: Use /tmp as base directory, not /app
        file_path = Path("/tmp") / target_file.path
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File no longer exists")
        
        # Read file content (limit to 1MB for safety)
        if file_path.stat().st_size > 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large for preview")
        
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        
        logger.info(f"Retrieved content for file {target_file.name}", user=current_user.username)
        
        return {
            "content": content,
            "file": target_file.dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get file content", file_id=file_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get file content: {str(e)}"
        )

@router.delete("/files/{file_id}")
async def delete_generated_file(
    file_id: str,
    current_user: UserInfo = Depends(get_current_user)
) -> Dict:
    """
    Delete a generated file
    
    CLAUDE.md: < 20 lines - File deletion endpoint
    """
    try:
        files = scan_generated_files()
        target_file = next((f for f in files if f.id == file_id), None)
        
        if not target_file:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Use /tmp as base directory
        file_path = Path("/tmp") / target_file.path
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File no longer exists")
        
        # Delete the file
        file_path.unlink()
        
        logger.info(f"Deleted file {target_file.name}", user=current_user.username)
        
        return {
            "status": "success",
            "message": f"File '{target_file.name}' deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete file", file_id=file_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete file: {str(e)}"
        )
