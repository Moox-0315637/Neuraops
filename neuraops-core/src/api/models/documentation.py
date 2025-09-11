"""
Documentation API Models
Pydantic models for documentation system with file-based content
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class DocTemplateMetadata(BaseModel):
    """Template metadata information"""
    version: str = Field(..., description="Template version")
    author: str = Field(..., description="Template author")
    created: datetime = Field(..., description="Creation date")
    updated: datetime = Field(..., description="Last update date")


class DocTemplate(BaseModel):
    """Documentation template with content from files"""
    id: str = Field(..., description="Unique template identifier")
    name: str = Field(..., description="Template display name")
    type: str = Field(..., description="Template type (docker, k8s, terraform, etc.)")
    language: str = Field(..., description="Programming/config language")
    description: str = Field(..., description="Template description")
    code: str = Field(..., description="Template code content")
    file_path: str = Field(..., description="Path to template file")
    deployment_instructions: List[str] = Field(default=[], description="Deployment steps")
    security_notes: List[str] = Field(default=[], description="Security considerations")
    recommendations: List[str] = Field(default=[], description="Best practice recommendations")
    metadata: DocTemplateMetadata = Field(..., description="Template metadata")


class DocSection(BaseModel):
    """Documentation section containing templates"""
    id: str = Field(..., description="Unique section identifier")
    title: str = Field(..., description="Section display title")
    order: int = Field(..., description="Display order")
    description: str = Field(..., description="Section description")
    templates: List[DocTemplate] = Field(default=[], description="Templates in this section")


class DocQuickLink(BaseModel):
    """Quick access links for documentation"""
    id: str = Field(..., description="Unique link identifier")
    title: str = Field(..., description="Link title")
    description: str = Field(..., description="Link description")
    icon: str = Field(..., description="Icon identifier")
    url: str = Field(..., description="Target URL")
    category: str = Field(..., description="Link category")


class DocumentationResponse(BaseModel):
    """Complete documentation response"""
    sections: List[DocSection] = Field(default=[], description="All documentation sections")
    quick_links: List[DocQuickLink] = Field(default=[], description="Quick access links")
    total_sections: int = Field(..., description="Total number of sections")
    total_templates: int = Field(..., description="Total number of templates")
    last_updated: datetime = Field(default_factory=datetime.now, description="Last update timestamp")