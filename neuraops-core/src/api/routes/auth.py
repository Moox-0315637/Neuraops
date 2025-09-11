"""
Routes d'authentification pour l'UI NeuraOps.

CLAUDE.md: Respect des 500 lignes maximum par fichier
CLAUDE.md: Safety-First - Authentification JWT sécurisée
CLAUDE.md: Single Responsibility - Authentification UI uniquement
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
import structlog
import asyncio

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import jwt
from passlib.context import CryptContext

from ..models.responses import APIResponse
from ...devops_commander.config import get_config
from ...integration.postgres_client import PostgreSQLClient

logger = structlog.get_logger()

# Configuration
router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer(auto_error=False)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
config = get_config()

# Database client for user management
db_client = PostgreSQLClient()

# Models pour l'authentification UI
class LoginRequest(BaseModel):
    """Requête de connexion utilisateur."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)

class LoginResponse(BaseModel):
    """Réponse de connexion avec token JWT."""
    token: str
    expires_in: int
    user: dict

class UserInfo(BaseModel):
    """Informations utilisateur."""
    id: str
    username: str
    email: Optional[str] = None
    role: str = "admin"  # Pour l'instant, tous admin
    last_login: Optional[datetime] = None

class RefreshTokenRequest(BaseModel):
    """Requête de rafraîchissement de token."""
    refresh_token: Optional[str] = None

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérification du mot de passe."""
    return pwd_context.verify(plain_password, hashed_password)

async def get_user(username: str) -> Optional[dict]:
    """Récupération utilisateur par nom depuis la base de données."""
    try:
        if not db_client.connected:
            await db_client.connect()
        
        user = await db_client.get_user_by_username(username)
        return user
    except Exception as e:
        logger.error("Failed to get user from database", username=username, error=str(e))
        return None

def create_access_token(user_data: dict) -> tuple[str, int]:
    """Création du token JWT."""
    expires_delta = timedelta(hours=24)
    expire_time = datetime.now(timezone.utc) + expires_delta
    
    payload = {
        "sub": user_data["username"],
        "user_id": str(user_data["id"]),
        "role": user_data["role"],
        "exp": expire_time,
        "iat": datetime.now(timezone.utc)
    }
    
    # Utiliser une clé secrète configurée
    secret_key = getattr(config, 'secret_key', 'neuraops-secret-key-change-in-production')
    token = jwt.encode(payload, secret_key, algorithm="HS256")
    
    return token, int(expires_delta.total_seconds())

def decode_token(token: str) -> Optional[dict]:
    """Décodage et validation du token JWT."""
    try:
        secret_key = getattr(config, 'secret_key', 'neuraops-secret-key-change-in-production')
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        return payload
    except jwt.PyJWTError:
        return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserInfo:
    """Récupération de l'utilisateur courant depuis le token."""
    try:
        # Vérifier si les credentials sont présents
        if credentials is None:
            logger.warning("No credentials provided")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        token = credentials.credentials
        logger.debug(f"Attempting to decode token: {token[:20]}...")
        
        payload = decode_token(token)
        logger.debug(f"Token payload: {payload}")
        
        if not payload:
            logger.warning("Token decode failed")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalide"
            )
        
        username = payload.get("sub")
        logger.debug(f"Looking for user: {username}")
        
        user = await get_user(username)
        logger.debug(f"User found: {user is not None}")
        
        if not user:
            logger.warning(f"User not found: {username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Utilisateur non trouvé"
            )
        
        logger.debug(f"Authentication successful for user: {username}")
        return UserInfo(
            id=str(user["id"]),
            username=user["username"],
            email=user.get("email"),
            role=user["role"],
            last_login=user.get("last_login")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

@router.post("/login", response_model=APIResponse[LoginResponse])
async def login(credentials: LoginRequest):
    """
    Authentification utilisateur UI.
    
    Returns:
        APIResponse avec token JWT et info utilisateur
    """
    try:
        # Vérification utilisateur depuis la base de données
        user = await get_user(credentials.username)
        if not user or not verify_password(credentials.password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Nom d'utilisateur ou mot de passe incorrect"
            )
        
        # Génération du token
        token, expires_in = create_access_token(user)
        
        # Mise à jour dernière connexion dans la base de données
        if db_client.connected:
            await db_client.update_user_last_login(credentials.username)
        
        login_response = LoginResponse(
            token=token,
            expires_in=expires_in,
            user={
                "id": str(user["id"]),
                "username": user["username"],
                "email": user.get("email"),
                "role": user["role"]
            }
        )
        
        return APIResponse(
            status="success",
            message=f"Connexion réussie pour {credentials.username}",
            data=login_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur lors de l'authentification", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de l'authentification"
        )

@router.post("/logout", response_model=APIResponse[dict])
async def logout(current_user: UserInfo = Depends(get_current_user)):
    """
    Déconnexion utilisateur.
    
    Note: Avec JWT, la déconnexion côté serveur est limitée.
    Le client doit supprimer le token.
    """
    return APIResponse(
        status="success",
        message="Déconnexion réussie",
        data={"message": "Token invalidé côté client"}
    )

@router.get("/me", response_model=APIResponse[UserInfo])
async def get_current_user_info(current_user: UserInfo = Depends(get_current_user)):
    """
    Récupération des informations utilisateur courant.
    """
    return APIResponse(
        status="success",
        message="Informations utilisateur récupérées",
        data=current_user
    )

@router.post("/refresh", response_model=APIResponse[LoginResponse])
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Rafraîchissement du token JWT.
    """
    try:
        # Récupération utilisateur pour nouveau token
        user = await get_user(current_user.username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Utilisateur non trouvé"
            )
        
        # Génération nouveau token
        token, expires_in = create_access_token(user)
        
        refresh_response = LoginResponse(
            token=token,
            expires_in=expires_in,
            user={
                "id": str(user["id"]),
                "username": user["username"],
                "email": user.get("email"),
                "role": user["role"]
            }
        )
        
        return APIResponse(
            status="success",
            message="Token rafraîchi avec succès",
            data=refresh_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur lors du rafraîchissement", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors du rafraîchissement"
        )