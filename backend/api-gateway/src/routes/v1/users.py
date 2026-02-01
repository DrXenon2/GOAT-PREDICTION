"""
GOAT PREDICTION ULTIMATE - Users Routes
Gestion des utilisateurs et profils
"""

from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, validator
import uuid
import hashlib
import secrets
from passlib.context import CryptContext

from ...models.user import (
    User, UserCreate, UserUpdate, UserStats, UserPreferences,
    UserLogin, UserLoginResponse, PasswordChange, PasswordReset,
    PasswordResetConfirm, EmailVerification, UserPublic, UserActivity
)

router = APIRouter()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ============================================
# MODELS ADDITIONNELS
# ============================================

class UserProfile(BaseModel):
    """Profil utilisateur complet"""
    user: User
    stats: UserStats
    preferences: UserPreferences
    recent_activity: List[UserActivity] = Field(default_factory=list)


class ProfileUpdate(BaseModel):
    """Mise à jour de profil"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    bio: Optional[str] = Field(None, max_length=500)
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    
    # Social links
    twitter: Optional[str] = None
    linkedin: Optional[str] = None
    website: Optional[str] = None


class NotificationSettings(BaseModel):
    """Paramètres de notification"""
    email_predictions: bool = True
    email_bets: bool = True
    email_marketing: bool = False
    
    push_predictions: bool = True
    push_bets: bool = True
    push_alerts: bool = True
    
    sms_alerts: bool = False


class SecuritySettings(BaseModel):
    """Paramètres de sécurité"""
    two_factor_enabled: bool = False
    login_notifications: bool = True
    session_timeout: int = 3600  # secondes


class UserSession(BaseModel):
    """Session utilisateur"""
    id: str
    user_id: uuid.UUID
    ip_address: str
    user_agent: str
    device: str
    location: Optional[str] = None
    created_at: datetime
    last_activity: datetime
    is_current: bool = False


# ============================================
# ROUTES - AUTHENTICATION
# ============================================

@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register_user(user_create: UserCreate) -> User:
    """
    📝 Inscription d'un nouvel utilisateur
    
    **Validation:**
    - Email unique
    - Username unique
    - Mot de passe fort
    
    **Process:**
    1. Validation des données
    2. Hash du mot de passe
    3. Création utilisateur
    4. Envoi email de vérification
    5. Création d'un token JWT
    """
    try:
        # Vérifier que l'email n'existe pas
        existing_email = await get_user_by_email(user_create.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cet email est déjà utilisé"
            )
        
        # Vérifier que le username n'existe pas
        existing_username = await get_user_by_username(user_create.username)
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ce nom d'utilisateur est déjà pris"
            )
        
        # Hasher le mot de passe
        hashed_password = pwd_context.hash(user_create.password)
        
        # Créer l'utilisateur
        user = User(
            id=uuid.uuid4(),
            email=user_create.email,
            username=user_create.username,
            first_name=user_create.first_name,
            last_name=user_create.last_name,
            hashed_password=hashed_password,
            is_verified=False,
            created_at=datetime.utcnow()
        )
        
        # Sauvegarder en DB
        saved_user = await create_user(user, hashed_password)
        
        # Générer token de vérification
        verification_token = secrets.token_urlsafe(32)
        await save_verification_token(saved_user.id, verification_token)
        
        # Envoyer email de vérification
        await send_verification_email(saved_user.email, verification_token)
        
        return saved_user
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'inscription: {str(e)}"
        )


@router.post("/login", response_model=UserLoginResponse)
async def login_user(user_login: UserLogin) -> UserLoginResponse:
    """
    🔐 Connexion utilisateur
    
    **Process:**
    1. Vérification email/password
    2. Génération tokens JWT
    3. Enregistrement de la session
    4. Log de l'activité
    """
    try:
        # Récupérer l'utilisateur
        user = await get_user_by_email(user_login.email)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou mot de passe incorrect"
            )
        
        # Vérifier le mot de passe
        if not pwd_context.verify(user_login.password, user.hashed_password):
            # Incrémenter les tentatives échouées
            await increment_failed_attempts(user.id)
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou mot de passe incorrect"
            )
        
        # Vérifier que le compte est actif
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Compte désactivé. Contactez le support."
            )
        
        # Réinitialiser les tentatives échouées
        await reset_failed_attempts(user.id)
        
        # Générer les tokens
        access_token = await create_access_token(user.id)
        refresh_token = await create_refresh_token(user.id)
        
        # Mettre à jour last_login
        await update_last_login(user.id)
        
        # Enregistrer la session
        await create_user_session(user.id, access_token)
        
        # Log de l'activité
        await log_user_activity(
            user.id,
            "user_login",
            "Connexion réussie"
        )
        
        return UserLoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=3600,
            user=user
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur de connexion: {str(e)}"
        )


@router.post("/logout")
async def logout_user(
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """
    🚪 Déconnexion utilisateur
    
    **Process:**
    1. Invalide le token actuel
    2. Supprime la session
    3. Log de l'activité
    """
    try:
        # Invalider le token
        await invalidate_token(current_user.id)
        
        # Supprimer la session
        await delete_user_session(current_user.id)
        
        # Log
        await log_user_activity(
            current_user.id,
            "user_logout",
            "Déconnexion"
        )
        
        return {"message": "Déconnexion réussie"}
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur de déconnexion: {str(e)}"
        )


@router.post("/refresh")
async def refresh_token(refresh_token: str) -> Dict[str, Any]:
    """
    🔄 Rafraîchit le token d'accès
    """
    try:
        # Vérifier le refresh token
        user_id = await verify_refresh_token(refresh_token)
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token invalide"
            )
        
        # Générer nouveau access token
        new_access_token = await create_access_token(user_id)
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": 3600
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur refresh: {str(e)}"
        )


# ============================================
# ROUTES - PROFILE
# ============================================

@router.get("/me", response_model=User)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    👤 Récupère le profil de l'utilisateur connecté
    """
    return current_user


@router.get("/me/profile", response_model=UserProfile)
async def get_full_profile(
    current_user: User = Depends(get_current_user)
) -> UserProfile:
    """
    📊 Profil complet avec stats et préférences
    """
    try:
        # Récupérer les stats
        stats = await get_user_stats(current_user.id)
        
        # Récupérer les préférences
        preferences = await get_user_preferences(current_user.id)
        
        # Récupérer l'activité récente
        recent_activity = await get_recent_activity(current_user.id, limit=10)
        
        return UserProfile(
            user=current_user,
            stats=stats,
            preferences=preferences,
            recent_activity=recent_activity
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur récupération profil: {str(e)}"
        )


@router.patch("/me", response_model=User)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user)
) -> User:
    """
    ✏️ Met à jour le profil utilisateur
    """
    try:
        # Vérifier l'email si modifié
        if user_update.email and user_update.email != current_user.email:
            existing = await get_user_by_email(user_update.email)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email déjà utilisé"
                )
        
        # Vérifier le username si modifié
        if user_update.username and user_update.username != current_user.username:
            existing = await get_user_by_username(user_update.username)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username déjà pris"
                )
        
        # Mettre à jour
        updated_user = await update_user(current_user.id, user_update)
        
        # Log
        await log_user_activity(
            current_user.id,
            "user_update",
            "Profil mis à jour"
        )
        
        return updated_user
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur mise à jour: {str(e)}"
        )


@router.post("/me/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """
    📸 Upload d'avatar
    
    **Validation:**
    - Format: JPG, PNG, WEBP
    - Taille max: 5MB
    - Dimensions: 512x512 recommandé
    """
    try:
        # Vérifier le type de fichier
        allowed_types = ["image/jpeg", "image/png", "image/webp"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Format non supporté. Utilisez JPG, PNG ou WEBP"
            )
        
        # Vérifier la taille
        contents = await file.read()
        if len(contents) > 5 * 1024 * 1024:  # 5MB
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Fichier trop volumineux (max 5MB)"
            )
        
        # Upload vers S3/storage
        avatar_url = await upload_file_to_storage(
            contents,
            f"avatars/{current_user.id}/{file.filename}",
            file.content_type
        )
        
        # Mettre à jour le profil
        await update_user_avatar(current_user.id, avatar_url)
        
        return {
            "message": "Avatar mis à jour",
            "avatar_url": avatar_url
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur upload: {str(e)}"
        )


# ============================================
# ROUTES - PREFERENCES
# ============================================

@router.get("/me/preferences", response_model=UserPreferences)
async def get_preferences(
    current_user: User = Depends(get_current_user)
) -> UserPreferences:
    """
    ⚙️ Récupère les préférences utilisateur
    """
    try:
        preferences = await get_user_preferences(current_user.id)
        return preferences
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )


@router.put("/me/preferences", response_model=UserPreferences)
async def update_preferences(
    preferences: UserPreferences,
    current_user: User = Depends(get_current_user)
) -> UserPreferences:
    """
    ⚙️ Met à jour les préférences
    """
    try:
        updated = await save_user_preferences(current_user.id, preferences)
        return updated
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )


@router.put("/me/notifications", response_model=NotificationSettings)
async def update_notification_settings(
    settings: NotificationSettings,
    current_user: User = Depends(get_current_user)
) -> NotificationSettings:
    """
    🔔 Met à jour les paramètres de notification
    """
    try:
        updated = await save_notification_settings(current_user.id, settings)
        return updated
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )


# ============================================
# ROUTES - SECURITY
# ============================================

@router.post("/me/password/change")
async def change_password(
    password_change: PasswordChange,
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """
    🔐 Changement de mot de passe
    """
    try:
        # Vérifier le mot de passe actuel
        user = await get_user_by_id(current_user.id)
        if not pwd_context.verify(password_change.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mot de passe actuel incorrect"
            )
        
        # Hasher le nouveau mot de passe
        new_hashed = pwd_context.hash(password_change.new_password)
        
        # Mettre à jour
        await update_user_password(current_user.id, new_hashed)
        
        # Invalider toutes les sessions sauf la courante
        await invalidate_other_sessions(current_user.id)
        
        # Log
        await log_user_activity(
            current_user.id,
            "password_change",
            "Mot de passe modifié"
        )
        
        # Envoyer email de confirmation
        await send_password_changed_email(current_user.email)
        
        return {"message": "Mot de passe modifié avec succès"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )


@router.post("/password/reset")
async def request_password_reset(
    password_reset: PasswordReset
) -> Dict[str, str]:
    """
    📧 Demande de réinitialisation de mot de passe
    """
    try:
        # Vérifier que l'utilisateur existe
        user = await get_user_by_email(password_reset.email)
        
        if user:
            # Générer token
            reset_token = secrets.token_urlsafe(32)
            
            # Sauvegarder avec expiration (1h)
            await save_reset_token(user.id, reset_token, expires_in=3600)
            
            # Envoyer email
            await send_password_reset_email(user.email, reset_token)
        
        # Réponse générique pour sécurité
        return {
            "message": "Si cet email existe, un lien de réinitialisation a été envoyé"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )


@router.post("/password/reset/confirm")
async def confirm_password_reset(
    reset_confirm: PasswordResetConfirm
) -> Dict[str, str]:
    """
    ✅ Confirme la réinitialisation de mot de passe
    """
    try:
        # Vérifier le token
        user_id = await verify_reset_token(reset_confirm.token)
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token invalide ou expiré"
            )
        
        # Hasher le nouveau mot de passe
        new_hashed = pwd_context.hash(reset_confirm.new_password)
        
        # Mettre à jour
        await update_user_password(user_id, new_hashed)
        
        # Invalider toutes les sessions
        await invalidate_all_sessions(user_id)
        
        # Supprimer le token
        await delete_reset_token(reset_confirm.token)
        
        # Log
        await log_user_activity(
            user_id,
            "password_reset",
            "Mot de passe réinitialisé"
        )
        
        return {"message": "Mot de passe réinitialisé avec succès"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )


@router.post("/email/verify")
async def verify_email(
    verification: EmailVerification
) -> Dict[str, str]:
    """
    ✉️ Vérifie l'email avec le token
    """
    try:
        # Vérifier le token
        user_id = await verify_email_token(verification.token)
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token invalide ou expiré"
            )
        
        # Marquer comme vérifié
        await mark_email_verified(user_id)
        
        # Supprimer le token
        await delete_verification_token(verification.token)
        
        return {"message": "Email vérifié avec succès"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )


@router.post("/email/resend-verification")
async def resend_verification_email(
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """
    📨 Renvoie l'email de vérification
    """
    try:
        if current_user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email déjà vérifié"
            )
        
        # Générer nouveau token
        verification_token = secrets.token_urlsafe(32)
        await save_verification_token(current_user.id, verification_token)
        
        # Envoyer email
        await send_verification_email(current_user.email, verification_token)
        
        return {"message": "Email de vérification envoyé"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )


@router.get("/me/sessions", response_model=List[UserSession])
async def list_active_sessions(
    current_user: User = Depends(get_current_user)
) -> List[UserSession]:
    """
    📱 Liste les sessions actives
    """
    try:
        sessions = await get_user_sessions(current_user.id)
        return sessions
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )


@router.delete("/me/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """
    🚫 Révoque une session spécifique
    """
    try:
        await delete_session(session_id, current_user.id)
        return {"message": "Session révoquée"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )


@router.delete("/me/sessions")
async def revoke_all_sessions(
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """
    🚫 Révoque toutes les sessions sauf la courante
    """
    try:
        await invalidate_other_sessions(current_user.id)
        return {"message": "Toutes les autres sessions ont été révoquées"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )


# ============================================
# ROUTES - STATS & ACTIVITY
# ============================================

@router.get("/me/stats", response_model=UserStats)
async def get_my_stats(
    current_user: User = Depends(get_current_user)
) -> UserStats:
    """
    📊 Statistiques personnelles
    """
    try:
        stats = await get_user_stats(current_user.id)
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )


@router.get("/me/activity", response_model=List[UserActivity])
async def get_my_activity(
    limit: int = 50,
    current_user: User = Depends(get_current_user)
) -> List[UserActivity]:
    """
    📜 Historique d'activité
    """
    try:
        activity = await get_recent_activity(current_user.id, limit)
        return activity
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )


# ============================================
# ROUTES - PUBLIC PROFILES
# ============================================

@router.get("/{username}/public", response_model=UserPublic)
async def get_public_profile(username: str) -> UserPublic:
    """
    👁️ Profil public d'un utilisateur
    """
    try:
        user = await get_user_by_username(username)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur non trouvé"
            )
        
        # Vérifier que le profil est public
        preferences = await get_user_preferences(user.id)
        if not preferences.public_profile:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Profil privé"
            )
        
        # Calculer l'accuracy
        stats = await get_user_stats(user.id)
        
        return UserPublic(
            id=user.id,
            username=user.username,
            avatar_url=user.avatar_url,
            bio=user.bio,
            subscription_tier=user.subscription_tier,
            total_predictions=stats.total_predictions,
            accuracy=stats.accuracy,
            created_at=user.created_at
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )


@router.delete("/me")
async def delete_account(
    password: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """
    🗑️ Supprime le compte utilisateur
    
    **Attention:** Action irréversible
    """
    try:
        # Vérifier le mot de passe
        user = await get_user_by_id(current_user.id)
        if not pwd_context.verify(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mot de passe incorrect"
            )
        
        # Annuler l'abonnement si actif
        await cancel_user_subscription(current_user.id)
        
        # Soft delete (marquer comme supprimé)
        await soft_delete_user(current_user.id)
        
        # Invalider toutes les sessions
        await invalidate_all_sessions(current_user.id)
        
        # Log
        await log_user_activity(
            current_user.id,
            "account_deleted",
            "Compte supprimé"
        )
        
        # Envoyer email de confirmation
        await send_account_deleted_email(current_user.email)
        
        return {"message": "Compte supprimé avec succès"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur: {str(e)}"
        )


# ============================================
# HELPER FUNCTIONS (à implémenter)
# ============================================

async def get_user_by_email(email: str):
    """Récupère un utilisateur par email"""
    # TODO: DB query
    return None

async def get_user_by_username(username: str):
    """Récupère un utilisateur par username"""
    # TODO: DB query
    return None

async def get_user_by_id(user_id: uuid.UUID):
    """Récupère un utilisateur par ID"""
    # TODO: DB query
    return None

async def create_user(user: User, hashed_password: str):
    """Crée un utilisateur"""
    # TODO: DB insert
    return user

async def update_user(user_id: uuid.UUID, user_update: UserUpdate):
    """Met à jour un utilisateur"""
    # TODO: DB update
    return None

async def increment_failed_attempts(user_id: uuid.UUID):
    """Incrémente les tentatives échouées"""
    # TODO: DB update
    pass

async def reset_failed_attempts(user_id: uuid.UUID):
    """Réinitialise les tentatives"""
    # TODO: DB update
    pass

async def create_access_token(user_id: uuid.UUID) -> str:
    """Crée un access token JWT"""
    # TODO: JWT generation
    return "access_token"

async def create_refresh_token(user_id: uuid.UUID) -> str:
    """Crée un refresh token"""
    # TODO: JWT generation
    return "refresh_token"

async def verify_refresh_token(token: str):
    """Vérifie un refresh token"""
    # TODO: JWT verification
    return None

async def update_last_login(user_id: uuid.UUID):
    """Met à jour last_login"""
    # TODO: DB update
    pass

async def create_user_session(user_id: uuid.UUID, token: str):
    """Crée une session"""
    # TODO: DB insert
    pass

async def delete_user_session(user_id: uuid.UUID):
    """Supprime la session courante"""
    # TODO: DB delete
    pass

async def invalidate_token(user_id: uuid.UUID):
    """Invalide le token"""
    # TODO: Redis/DB
    pass

async def log_user_activity(user_id: uuid.UUID, activity_type: str, description: str):
    """Log une activité"""
    # TODO: DB insert
    pass

async def get_user_stats(user_id: uuid.UUID) -> UserStats:
    """Récupère les stats"""
    # TODO: DB query
    return UserStats(user_id=user_id)

async def get_user_preferences(user_id: uuid.UUID) -> UserPreferences:
    """Récupère les préférences"""
    # TODO: DB query
    return UserPreferences(user_id=user_id)

async def save_user_preferences(user_id: uuid.UUID, preferences: UserPreferences):
    """Sauvegarde les préférences"""
    # TODO: DB update
    return preferences

async def get_recent_activity(user_id: uuid.UUID, limit: int) -> List[UserActivity]:
    """Récupère l'activité récente"""
    # TODO: DB query
    return []

async def save_verification_token(user_id: uuid.UUID, token: str):
    """Sauvegarde le token de vérification"""
    # TODO: DB insert
    pass

async def verify_email_token(token: str):
    """Vérifie le token email"""
    # TODO: DB query
    return None

async def mark_email_verified(user_id: uuid.UUID):
    """Marque l'email comme vérifié"""
    # TODO: DB update
    pass

async def send_verification_email(email: str, token: str):
    """Envoie l'email de vérification"""
    # TODO: Email service
    pass

async def send_password_reset_email(email: str, token: str):
    """Envoie l'email de reset"""
    # TODO: Email service
    pass

async def send_password_changed_email(email: str):
    """Envoie l'email de confirmation"""
    # TODO: Email service
    pass

async def send_account_deleted_email(email: str):
    """Envoie l'email de suppression"""
    # TODO: Email service
    pass

async def update_user_password(user_id: uuid.UUID, hashed_password: str):
    """Met à jour le mot de passe"""
    # TODO: DB update
    pass

async def update_user_avatar(user_id: uuid.UUID, avatar_url: str):
    """Met à jour l'avatar"""
    # TODO: DB update
    pass

async def upload_file_to_storage(contents: bytes, path: str, content_type: str) -> str:
    """Upload un fichier vers S3/storage"""
    # TODO: S3/storage upload
    return f"https://cdn.example.com/{path}"

async def save_reset_token(user_id: uuid.UUID, token: str, expires_in: int):
    """Sauvegarde le token de reset"""
    # TODO: DB insert avec expiration
    pass

async def verify_reset_token(token: str):
    """Vérifie le token de reset"""
    # TODO: DB query
    return None

async def delete_reset_token(token: str):
    """Supprime le token"""
    # TODO: DB delete
    pass

async def delete_verification_token(token: str):
    """Supprime le token de vérification"""
    # TODO: DB delete
    pass

async def invalidate_other_sessions(user_id: uuid.UUID):
    """Invalide les autres sessions"""
    # TODO: DB/Redis
    pass

async def invalidate_all_sessions(user_id: uuid.UUID):
    """Invalide toutes les sessions"""
    # TODO: DB/Redis
    pass

async def get_user_sessions(user_id: uuid.UUID) -> List[UserSession]:
    """Récupère les sessions"""
    # TODO: DB query
    return []

async def delete_session(session_id: str, user_id: uuid.UUID):
    """Supprime une session"""
    # TODO: DB delete
    pass

async def save_notification_settings(user_id: uuid.UUID, settings: NotificationSettings):
    """Sauvegarde les paramètres de notification"""
    # TODO: DB update
    return settings

async def cancel_user_subscription(user_id: uuid.UUID):
    """Annule l'abonnement"""
    # TODO: Stripe + DB
    pass

async def soft_delete_user(user_id: uuid.UUID):
    """Suppression soft (marquer comme supprimé)"""
    # TODO: DB update
    pass
