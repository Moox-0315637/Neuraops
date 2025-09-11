"""
Documentation Service
Service for reading documentation from YAML configs and template files
"""

import os
import yaml
import aiofiles
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from ..models.documentation import (
    DocSection, 
    DocTemplate, 
    DocQuickLink, 
    DocTemplateMetadata,
    DocumentationResponse
)


class DocumentationService:
    """Service for managing file-based documentation system"""
    
    def __init__(self, data_path: str = None):
        """Initialize documentation service with data directory path"""
        if data_path is None:
            # Default to data directory relative to project root
            current_dir = Path(__file__).parent.parent.parent.parent
            self.data_path = current_dir / "data" / "documentation"
        else:
            self.data_path = Path(data_path)
        
        self.sections_file = self.data_path / "sections.yaml"
        self.quick_links_file = self.data_path / "quick-links.yaml"
        self.templates_dir = self.data_path / "templates"
    
    async def load_sections(self) -> List[DocSection]:
        """Load documentation sections from YAML config"""
        try:
            if not self.sections_file.exists():
                return []
            
            async with aiofiles.open(self.sections_file, 'r', encoding='utf-8') as file:
                content = await file.read()
                data = yaml.safe_load(content)
            
            sections = []
            for section_data in data.get('sections', []):
                # Load templates for this section
                templates = []
                for template_data in section_data.get('templates', []):
                    template = await self._load_template(template_data)
                    if template:
                        templates.append(template)
                
                section = DocSection(
                    id=section_data['id'],
                    title=section_data['title'],
                    order=section_data['order'],
                    description=section_data['description'],
                    templates=templates
                )
                sections.append(section)
            
            return sorted(sections, key=lambda x: x.order)
            
        except Exception as e:
            print(f"Error loading sections: {e}")
            return []
    
    async def _load_template(self, template_data: Dict[str, Any]) -> Optional[DocTemplate]:
        """Load individual template with code content from file"""
        try:
            # Read template code from file
            template_file = self.templates_dir / template_data['file_path']
            code_content = ""
            
            if template_file.exists():
                async with aiofiles.open(template_file, 'r', encoding='utf-8') as file:
                    code_content = await file.read()
            
            # Parse metadata dates
            metadata = DocTemplateMetadata(
                version=template_data['version'],
                author=template_data['author'],
                created=datetime.fromisoformat(template_data['created']),
                updated=datetime.fromisoformat(template_data['updated'])
            )
            
            return DocTemplate(
                id=template_data['id'],
                name=template_data['name'],
                type=template_data['type'],
                language=template_data['language'],
                description=template_data['description'],
                code=code_content,
                file_path=template_data['file_path'],
                deployment_instructions=template_data.get('deployment_instructions', []),
                security_notes=template_data.get('security_notes', []),
                recommendations=template_data.get('recommendations', []),
                metadata=metadata
            )
            
        except Exception as e:
            print(f"Error loading template {template_data.get('id', 'unknown')}: {e}")
            return None
    
    async def load_quick_links(self) -> List[DocQuickLink]:
        """Load quick links from YAML config"""
        try:
            if not self.quick_links_file.exists():
                return []
            
            async with aiofiles.open(self.quick_links_file, 'r', encoding='utf-8') as file:
                content = await file.read()
                data = yaml.safe_load(content)
            
            links = []
            for link_data in data.get('quick_links', []):
                link = DocQuickLink(**link_data)
                links.append(link)
            
            return links
            
        except Exception as e:
            print(f"Error loading quick links: {e}")
            return []
    
    async def get_template_by_id(self, template_id: str) -> Optional[DocTemplate]:
        """Get specific template by ID"""
        sections = await self.load_sections()
        for section in sections:
            for template in section.templates:
                if template.id == template_id:
                    return template
        return None
    
    async def get_templates_by_section(self, section_id: str) -> List[DocTemplate]:
        """Get all templates in a specific section"""
        sections = await self.load_sections()
        for section in sections:
            if section.id == section_id:
                return section.templates
        return []
    
    async def get_complete_documentation(self) -> DocumentationResponse:
        """Get complete documentation data"""
        sections = await self.load_sections()
        quick_links = await self.load_quick_links()
        
        total_templates = sum(len(section.templates) for section in sections)
        
        return DocumentationResponse(
            sections=sections,
            quick_links=quick_links,
            total_sections=len(sections),
            total_templates=total_templates,
            last_updated=datetime.now()
        )
    
    def health_check(self) -> Dict[str, Any]:
        """Check service health and file availability"""
        return {
            "service": "documentation",
            "status": "healthy",
            "data_path": str(self.data_path),
            "files": {
                "sections_config": self.sections_file.exists(),
                "quick_links_config": self.quick_links_file.exists(),
                "templates_directory": self.templates_dir.exists()
            }
        }

    async def get_all_templates(self) -> List[DocTemplate]:
        """Get all templates from all sections"""
        sections = await self.load_sections()
        templates = []
        for section in sections:
            templates.extend(section.templates)
        return templates
    
    async def get_templates_from_filesystem(self) -> List[Dict[str, Any]]:
        """Get templates by scanning filesystem directly following CLAUDE.md < 10 lines"""
        templates = []
        
        if not self.templates_dir.exists():
            return templates
        
        # Scan all sections and collect templates
        for section_dir in self._scan_section_directories():
            section_templates = await self._process_section_templates(section_dir)
            templates.extend(section_templates)
        
        return templates
    
    def _scan_section_directories(self) -> List:
        """Scan section directories following CLAUDE.md < 5 lines"""
        return [d for d in self.templates_dir.iterdir() if d.is_dir()]

    async def _process_section_templates(self, section_dir) -> List[Dict[str, Any]]:
        """Process all template files in a section following CLAUDE.md < 10 lines"""
        templates = []
        section_id = section_dir.name
        
        for template_file in section_dir.iterdir():
            if template_file.is_file():
                template_info = await self._process_template_file(template_file, section_id)
                if template_info:
                    templates.append(template_info)
        
        return templates

    async def _process_template_file(self, template_file, section_id: str) -> Optional[Dict[str, Any]]:
        """Process individual template file following CLAUDE.md < 15 lines"""
        try:
            # Read file content
            async with aiofiles.open(template_file, 'r', encoding='utf-8') as file:
                content = await file.read()
            
            return self._create_template_info(template_file, section_id, content)
            
        except Exception as e:
            print(f"Error reading template {template_file}: {e}")
            return None

    def _create_template_info(self, template_file, section_id: str, content: str) -> Dict[str, Any]:
        """Create template info dict following CLAUDE.md < 10 lines"""
        stat = template_file.stat()
        created_time = datetime.fromtimestamp(stat.st_ctime)
        modified_time = datetime.fromtimestamp(stat.st_mtime)
        
        return {
            "file_name": template_file.name,
            "file_path": f"{section_id}/{template_file.name}",
            "section_id": section_id,
            "content": content,
            "size": stat.st_size,
            "created": created_time.isoformat(),
            "modified": modified_time.isoformat(),
            "extension": template_file.suffix
        }
    
    async def upload_template(self, section_id: str, filename: str, content: str) -> Dict[str, Any]:
        """Upload a new template file"""
        try:
            # Create section directory if it doesn't exist
            section_dir = self.templates_dir / section_id
            section_dir.mkdir(parents=True, exist_ok=True)
            
            # Write template file
            template_path = section_dir / filename
            async with aiofiles.open(template_path, 'w', encoding='utf-8') as file:
                await file.write(content)
            
            # Get file stats
            stat = template_path.stat()
            
            return {
                "status": "success",
                "message": f"Template {filename} uploaded successfully",
                "file_path": f"{section_id}/{filename}",
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat()
            }
            
        except Exception as e:
            return {
                "status": "error", 
                "message": f"Failed to upload template: {str(e)}"
            }
    
    def delete_template(self, section_id: str, filename: str) -> Dict[str, Any]:
        """Delete a template file"""
        try:
            template_path = self.templates_dir / section_id / filename
            
            if not template_path.exists():
                return {
                    "status": "error",
                    "message": f"Template {filename} not found in section {section_id}"
                }
            
            # Delete the file
            template_path.unlink()
            
            # Check if section directory is empty and remove if needed
            section_dir = self.templates_dir / section_id
            if section_dir.exists() and not any(section_dir.iterdir()):
                section_dir.rmdir()
            
            return {
                "status": "success",
                "message": f"Template {filename} deleted successfully"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to delete template: {str(e)}"
            }
    
    async def get_template_content(self, section_id: str, filename: str) -> Optional[str]:
        """Get raw content of a specific template file"""
        try:
            template_path = self.templates_dir / section_id / filename
            
            if not template_path.exists():
                return None
            
            async with aiofiles.open(template_path, 'r', encoding='utf-8') as file:
                return await file.read()
                
        except Exception as e:
            print(f"Error reading template content: {e}")
            return None
    
    async def update_template(self, section_id: str, filename: str, content: str) -> Dict[str, Any]:
        """Update existing template file"""
        try:
            template_path = self.templates_dir / section_id / filename
            
            if not template_path.exists():
                return {
                    "status": "error",
                    "message": f"Template {filename} not found in section {section_id}"
                }
            
            # Update file content
            async with aiofiles.open(template_path, 'w', encoding='utf-8') as file:
                await file.write(content)
            
            # Get updated file stats
            stat = template_path.stat()
            
            return {
                "status": "success",
                "message": f"Template {filename} updated successfully",
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to update template: {str(e)}"
            }
