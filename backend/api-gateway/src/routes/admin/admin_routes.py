"""
GOAT PREDICTION ULTIMATE - Admin General Routes
Routes générales d'administration
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List
from datetime import datetime, timedelta

from ...models.user import User, UserRole
from .models import (
    AdminDashboard,
    AdminStats,
    ActivityLog,
    SystemAlert,
)

router = APIRouter()


@router.get("/dashboard", response_model=AdminDashboard)
async def get_admin_dashboard(
    current_user: User = Depends(get_current_admin_user)
) -> AdminDashboard:
    """
    📊 Récupère le dashboard admin
    
    **Permissions:** Admin uniquement
    
    Retourne:
    - Vue d'ensemble du système
    - Statistiques clés
    - Activité récente
    - Alertes système
    """
    try:
        # Récupérer les statistiques
        stats = await get_system_stats()
        
        # Récupérer l'activité récente
        recent_activity = await get_recent_activity(limit=20)
        
        # Récupérer les alertes
        alerts = await get_system_alerts(active_only=True)
        
        # Récupérer les métriques en temps réel
        realtime_metrics = await get_realtime_metrics()
        
        dashboard = AdminDashboard(
            stats=stats,
            recent_activity=recent_activity,
            alerts=alerts,
            realtime_metrics=realtime_metrics,
            timestamp=datetime.utcnow()
        )
        
        return dashboard
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération du dashboard: {str(e)}"
        )


@router.get("/stats", response_model=AdminStats)
async def get_admin_stats(
    period: str = "7d",
    current_user: User = Depends(get_current_admin_user)
) -> AdminStats:
    """
    📈 Récupère les statistiques administrateur
    
    **Paramètres:**
    - period: Période ('24h', '7d', '30d', '90d', '1y')
    
    **Permissions:** Admin uniquement
    """
    try:
        # Calculer les dates
        end_date = datetime.utcnow()
        
        period_map = {
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
            "90d": timedelta(days=90),
            "1y": timedelta(days=365),
        }
        
        if period not in period_map:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Période invalide. Options: {', '.join(period_map.keys())}"
            )
        
        start_date = end_date - period_map[period]
        
        # Récupérer les stats
        stats = await calculate_admin_stats(start_date, end_date)
        
        return stats
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des stats: {str(e)}"
        )


@router.get("/activity", response_model=List[ActivityLog])
async def get_activity_logs(
    limit: int = 50,
    offset: int = 0,
    activity_type: Optional[str] = None,
    user_id: Optional[str] = None,
    current_user: User = Depends(get_current_admin_user)
) -> List[ActivityLog]:
    """
    📋 Récupère les logs d'activité
    
    **Paramètres:**
    - limit: Nombre de résultats (max 100)
    - offset: Pagination
    - activity_type: Filtrer par type
    - user_id: Filtrer par utilisateur
    
    **Permissions:** Admin uniquement
    """
    try:
        if limit > 100:
            limit = 100
        
        # Récupérer les logs
        logs = await fetch_activity_logs(
            limit=limit,
            offset=offset,
            activity_type=activity_type,
            user_id=user_id
        )
        
        return logs
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des logs: {str(e)}"
        )


@router.get("/alerts", response_model=List[SystemAlert])
async def get_alerts(
    active_only: bool = True,
    severity: Optional[str] = None,
    current_user: User = Depends(get_current_admin_user)
) -> List[SystemAlert]:
    """
    🚨 Récupère les alertes système
    
    **Paramètres:**
    - active_only: Seulement les alertes actives
    - severity: Filtrer par sévérité (info, warning, error, critical)
    
    **Permissions:** Admin uniquement
    """
    try:
        alerts = await get_system_alerts(
            active_only=active_only,
            severity=severity
        )
        
        return alerts
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des alertes: {str(e)}"
        )


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    ✅ Acquitte une alerte
    
    **Permissions:** Admin uniquement
    """
    try:
        result = await acknowledge_system_alert(alert_id, current_user.id)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alerte non trouvée"
            )
        
        return {
            "message": "Alerte acquittée avec succès",
            "alert_id": alert_id,
            "acknowledged_by": str(current_user.id),
            "acknowledged_at": datetime.utcnow().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'acquittement: {str(e)}"
        )


@router.get("/metrics/realtime")
async def get_realtime_metrics(
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    ⚡ Récupère les métriques en temps réel
    
    **Permissions:** Admin uniquement
    
    Retourne:
    - Requêtes par seconde
    - Utilisateurs actifs
    - Charge serveur
    - Latence moyenne
    """
    try:
        metrics = await fetch_realtime_metrics()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": metrics
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des métriques: {str(e)}"
        )


@router.post("/cache/clear")
async def clear_cache(
    cache_type: Optional[str] = None,
    current_user: User = Depends(get_current_superadmin_user)
) -> Dict[str, Any]:
    """
    🗑️ Vide le cache
    
    **Paramètres:**
    - cache_type: Type de cache ('all', 'predictions', 'users', 'analytics')
    
    **Permissions:** Superadmin uniquement
    """
    try:
        result = await clear_system_cache(cache_type)
        
        return {
            "message": "Cache vidé avec succès",
            "cache_type": cache_type or "all",
            "keys_cleared": result.get("keys_cleared", 0),
            "cleared_at": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du vidage du cache: {str(e)}"
        )


# ============================================
# HELPER FUNCTIONS
# ============================================

async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Vérifie que l'utilisateur est admin"""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs"
        )
    return current_user


async def get_current_superadmin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Vérifie que l'utilisateur est superadmin"""
    if current_user.role != UserRole.SUPERADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux super-administrateurs"
        )
    return current_user


async def get_system_stats() -> AdminStats:
    """Récupère les statistiques système"""
    # TODO: Implémenter la récupération depuis la DB
    return AdminStats(
        total_users=0,
        active_users=0,
        total_predictions=0,
        total_bets=0,
        system_uptime=0,
        api_requests_today=0
    )


async def get_recent_activity(limit: int = 20) -> List[ActivityLog]:
    """Récupère l'activité récente"""
    # TODO: Implémenter
    return []


async def get_system_alerts(
    active_only: bool = True,
    severity: Optional[str] = None
) -> List[SystemAlert]:
    """Récupère les alertes système"""
    # TODO: Implémenter
    return []


async def fetch_realtime_metrics() -> Dict[str, Any]:
    """Récupère les métriques temps réel"""
    # TODO: Implémenter
    return {}
