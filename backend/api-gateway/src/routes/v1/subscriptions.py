"""
GOAT PREDICTION ULTIMATE - Subscriptions Routes
Gestion des abonnements et paiements Stripe
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, EmailStr
from enum import Enum
import uuid
import stripe
import hmac
import hashlib

from ...models.user import User, SubscriptionTier
from ...config.settings import get_settings

router = APIRouter()
settings = get_settings()

# Configuration Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


# ============================================
# MODELS
# ============================================

class SubscriptionStatus(str, Enum):
    """Statuts d'abonnement"""
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"
    TRIALING = "trialing"
    PAUSED = "paused"


class BillingCycle(str, Enum):
    """Cycles de facturation"""
    MONTHLY = "monthly"
    YEARLY = "yearly"


class PlanFeature(BaseModel):
    """Fonctionnalité d'un plan"""
    name: str
    description: str
    included: bool
    limit: Optional[int] = None


class SubscriptionPlan(BaseModel):
    """Plan d'abonnement"""
    id: str
    name: str
    tier: SubscriptionTier
    
    # Prix
    monthly_price: float
    yearly_price: float
    currency: str = "USD"
    
    # IDs Stripe
    stripe_monthly_price_id: Optional[str] = None
    stripe_yearly_price_id: Optional[str] = None
    
    # Features
    features: List[PlanFeature] = Field(default_factory=list)
    
    # Limites
    max_predictions_per_day: Optional[int] = None
    max_bets_per_day: Optional[int] = None
    api_access: bool = False
    advanced_analytics: bool = False
    custom_models: bool = False
    priority_support: bool = False
    
    # Marketing
    popular: bool = False
    discount_percentage: Optional[int] = None
    trial_days: int = 0


class Subscription(BaseModel):
    """Abonnement utilisateur"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID
    
    # Plan
    plan_id: str
    tier: SubscriptionTier
    
    # Stripe
    stripe_subscription_id: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    
    # Status
    status: SubscriptionStatus
    billing_cycle: BillingCycle
    
    # Dates
    current_period_start: datetime
    current_period_end: datetime
    trial_end: Optional[datetime] = None
    canceled_at: Optional[datetime] = None
    
    # Paiement
    next_billing_date: Optional[datetime] = None
    amount: float
    currency: str = "USD"
    
    # Auto-renewal
    auto_renew: bool = True
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        orm_mode = True
        use_enum_values = True


class SubscriptionCreate(BaseModel):
    """Création d'abonnement"""
    plan_id: str
    billing_cycle: BillingCycle
    payment_method_id: str
    use_trial: bool = True


class SubscriptionUpdate(BaseModel):
    """Mise à jour d'abonnement"""
    plan_id: Optional[str] = None
    billing_cycle: Optional[BillingCycle] = None
    auto_renew: Optional[bool] = None


class PaymentMethod(BaseModel):
    """Méthode de paiement"""
    id: str
    type: str
    card_brand: Optional[str] = None
    card_last4: Optional[str] = None
    card_exp_month: Optional[int] = None
    card_exp_year: Optional[int] = None
    is_default: bool = False


class Invoice(BaseModel):
    """Facture"""
    id: str
    user_id: uuid.UUID
    
    amount: float
    currency: str
    status: str
    
    invoice_pdf: Optional[str] = None
    invoice_number: Optional[str] = None
    
    billing_reason: Optional[str] = None
    
    created_at: datetime
    paid_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True


class CheckoutSession(BaseModel):
    """Session de paiement"""
    session_id: str
    url: str
    expires_at: datetime


# ============================================
# ROUTES - PLANS
# ============================================

@router.get("/plans", response_model=List[SubscriptionPlan])
async def get_subscription_plans() -> List[SubscriptionPlan]:
    """
    💎 Liste tous les plans d'abonnement disponibles
    
    **Retourne:**
    - Tous les plans avec features
    - Prix mensuels et annuels
    - Limites et avantages
    """
    plans = [
        SubscriptionPlan(
            id="basic",
            name="Basic",
            tier=SubscriptionTier.BASIC,
            monthly_price=14.99,
            yearly_price=149.99,
            stripe_monthly_price_id="price_basic_monthly",
            stripe_yearly_price_id="price_basic_yearly",
            features=[
                PlanFeature(name="Prédictions quotidiennes", description="50 prédictions/jour", included=True, limit=50),
                PlanFeature(name="Sports multiples", description="Football, Basketball, Tennis", included=True),
                PlanFeature(name="Analytics basiques", description="Statistiques de base", included=True),
                PlanFeature(name="Support email", description="Réponse sous 48h", included=True),
                PlanFeature(name="API Access", description="Accès API", included=False),
                PlanFeature(name="Modèles personnalisés", description="Créez vos modèles", included=False),
            ],
            max_predictions_per_day=50,
            max_bets_per_day=20,
            api_access=False,
            advanced_analytics=False,
            trial_days=7
        ),
        SubscriptionPlan(
            id="premium",
            name="Premium",
            tier=SubscriptionTier.PREMIUM,
            monthly_price=49.99,
            yearly_price=499.99,
            stripe_monthly_price_id="price_premium_monthly",
            stripe_yearly_price_id="price_premium_yearly",
            features=[
                PlanFeature(name="Prédictions illimitées", description="Prédictions illimitées", included=True),
                PlanFeature(name="Tous les sports", description="Tous les sports disponibles", included=True),
                PlanFeature(name="Analytics avancées", description="ML insights, comparaisons", included=True),
                PlanFeature(name="Prédictions live", description="Prédictions en temps réel", included=True),
                PlanFeature(name="Support prioritaire", description="Réponse sous 24h", included=True),
                PlanFeature(name="API Access", description="1000 req/jour", included=True, limit=1000),
                PlanFeature(name="Modèles personnalisés", description="Créez vos modèles", included=False),
            ],
            max_predictions_per_day=None,  # Illimité
            max_bets_per_day=100,
            api_access=True,
            advanced_analytics=True,
            priority_support=True,
            popular=True,
            trial_days=14
        ),
        SubscriptionPlan(
            id="vip",
            name="VIP",
            tier=SubscriptionTier.VIP,
            monthly_price=199.99,
            yearly_price=1999.99,
            stripe_monthly_price_id="price_vip_monthly",
            stripe_yearly_price_id="price_vip_yearly",
            features=[
                PlanFeature(name="Tout Premium +", description="Toutes les features Premium", included=True),
                PlanFeature(name="Modèles personnalisés", description="Créez et entraînez vos modèles", included=True),
                PlanFeature(name="API illimitée", description="Requêtes illimitées", included=True),
                PlanFeature(name="Support dédié", description="Manager dédié", included=True),
                PlanFeature(name="Beta features", description="Accès anticipé aux nouveautés", included=True),
                PlanFeature(name="Consultation ML", description="1h/mois avec data scientist", included=True),
                PlanFeature(name="White label", description="Votre marque", included=True),
            ],
            max_predictions_per_day=None,
            max_bets_per_day=None,
            api_access=True,
            advanced_analytics=True,
            custom_models=True,
            priority_support=True,
            discount_percentage=20,
            trial_days=30
        )
    ]
    
    return plans


@router.get("/plans/{plan_id}", response_model=SubscriptionPlan)
async def get_plan_details(plan_id: str) -> SubscriptionPlan:
    """
    🔍 Détails d'un plan spécifique
    """
    plans = await get_subscription_plans()
    plan = next((p for p in plans if p.id == plan_id), None)
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan non trouvé"
        )
    
    return plan


# ============================================
# ROUTES - SUBSCRIPTION
# ============================================

@router.get("/current", response_model=Subscription)
async def get_current_subscription(
    current_user: User = Depends(get_current_user)
) -> Subscription:
    """
    📊 Récupère l'abonnement actuel de l'utilisateur
    """
    try:
        subscription = await fetch_user_subscription(current_user.id)
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aucun abonnement actif"
            )
        
        return subscription
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur récupération abonnement: {str(e)}"
        )


@router.post("/checkout", response_model=CheckoutSession)
async def create_checkout_session(
    subscription_create: SubscriptionCreate,
    current_user: User = Depends(get_current_user)
) -> CheckoutSession:
    """
    🛒 Crée une session de paiement Stripe
    
    **Process:**
    1. Vérifie le plan
    2. Crée/récupère le customer Stripe
    3. Crée la session de checkout
    4. Retourne l'URL de paiement
    """
    try:
        # Vérifier que le plan existe
        plans = await get_subscription_plans()
        plan = next((p for p in plans if p.id == subscription_create.plan_id), None)
        
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan non trouvé"
            )
        
        # Récupérer ou créer le customer Stripe
        stripe_customer = await get_or_create_stripe_customer(current_user)
        
        # Déterminer le price_id selon le cycle
        if subscription_create.billing_cycle == BillingCycle.MONTHLY:
            price_id = plan.stripe_monthly_price_id
        else:
            price_id = plan.stripe_yearly_price_id
        
        # Créer la session Stripe
        session = stripe.checkout.Session.create(
            customer=stripe_customer.id,
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=f"{settings.APP_URL}/subscription/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.APP_URL}/subscription/cancel",
            metadata={
                'user_id': str(current_user.id),
                'plan_id': subscription_create.plan_id,
                'billing_cycle': subscription_create.billing_cycle
            },
            subscription_data={
                'trial_period_days': plan.trial_days if subscription_create.use_trial else 0,
                'metadata': {
                    'user_id': str(current_user.id),
                    'plan_id': subscription_create.plan_id
                }
            }
        )
        
        return CheckoutSession(
            session_id=session.id,
            url=session.url,
            expires_at=datetime.fromtimestamp(session.expires_at)
        )
    
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur Stripe: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur création session: {str(e)}"
        )


@router.patch("/current", response_model=Subscription)
async def update_subscription(
    subscription_update: SubscriptionUpdate,
    current_user: User = Depends(get_current_user)
) -> Subscription:
    """
    ✏️ Met à jour l'abonnement actuel
    
    **Permet de:**
    - Changer de plan (upgrade/downgrade)
    - Changer de cycle de facturation
    - Activer/désactiver le renouvellement auto
    """
    try:
        # Récupérer l'abonnement actuel
        current_sub = await fetch_user_subscription(current_user.id)
        
        if not current_sub:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aucun abonnement actif"
            )
        
        # Changer de plan si demandé
        if subscription_update.plan_id and subscription_update.plan_id != current_sub.plan_id:
            await change_subscription_plan(
                current_user.id,
                current_sub.stripe_subscription_id,
                subscription_update.plan_id,
                subscription_update.billing_cycle or current_sub.billing_cycle
            )
        
        # Mettre à jour le renouvellement auto
        if subscription_update.auto_renew is not None:
            await update_auto_renew(
                current_sub.stripe_subscription_id,
                subscription_update.auto_renew
            )
        
        # Récupérer l'abonnement mis à jour
        updated_sub = await fetch_user_subscription(current_user.id)
        
        return updated_sub
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur mise à jour abonnement: {str(e)}"
        )


@router.post("/cancel")
async def cancel_subscription(
    immediate: bool = False,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    ❌ Annule l'abonnement
    
    **Paramètres:**
    - immediate: Si True, annulation immédiate. Sinon, à la fin de la période
    """
    try:
        subscription = await fetch_user_subscription(current_user.id)
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aucun abonnement actif"
            )
        
        # Annuler dans Stripe
        if immediate:
            stripe.Subscription.delete(subscription.stripe_subscription_id)
            end_date = datetime.utcnow()
        else:
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=True
            )
            end_date = subscription.current_period_end
        
        # Mettre à jour en DB
        await update_subscription_status(
            subscription.id,
            SubscriptionStatus.CANCELED,
            end_date
        )
        
        return {
            "message": "Abonnement annulé avec succès",
            "immediate": immediate,
            "end_date": end_date.isoformat(),
            "refund_eligible": immediate and (datetime.utcnow() - subscription.current_period_start).days < 7
        }
    
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur Stripe: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur annulation: {str(e)}"
        )


@router.post("/reactivate")
async def reactivate_subscription(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    🔄 Réactive un abonnement annulé
    
    **Conditions:**
    - L'abonnement doit être annulé mais pas encore expiré
    """
    try:
        subscription = await fetch_user_subscription(current_user.id)
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aucun abonnement trouvé"
            )
        
        if subscription.status != SubscriptionStatus.CANCELED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="L'abonnement n'est pas annulé"
            )
        
        if datetime.utcnow() > subscription.current_period_end:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="L'abonnement a expiré. Créez un nouvel abonnement."
            )
        
        # Réactiver dans Stripe
        stripe.Subscription.modify(
            subscription.stripe_subscription_id,
            cancel_at_period_end=False
        )
        
        # Mettre à jour en DB
        await update_subscription_status(
            subscription.id,
            SubscriptionStatus.ACTIVE,
            None
        )
        
        return {
            "message": "Abonnement réactivé avec succès",
            "next_billing_date": subscription.current_period_end.isoformat()
        }
    
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur Stripe: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur réactivation: {str(e)}"
        )


# ============================================
# ROUTES - PAYMENT METHODS
# ============================================

@router.get("/payment-methods", response_model=List[PaymentMethod])
async def list_payment_methods(
    current_user: User = Depends(get_current_user)
) -> List[PaymentMethod]:
    """
    💳 Liste les méthodes de paiement
    """
    try:
        subscription = await fetch_user_subscription(current_user.id)
        
        if not subscription or not subscription.stripe_customer_id:
            return []
        
        # Récupérer les payment methods depuis Stripe
        payment_methods = stripe.PaymentMethod.list(
            customer=subscription.stripe_customer_id,
            type='card'
        )
        
        methods = []
        for pm in payment_methods.data:
            methods.append(PaymentMethod(
                id=pm.id,
                type=pm.type,
                card_brand=pm.card.brand,
                card_last4=pm.card.last4,
                card_exp_month=pm.card.exp_month,
                card_exp_year=pm.card.exp_year,
                is_default=False  # TODO: Vérifier si c'est la méthode par défaut
            ))
        
        return methods
    
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur Stripe: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur récupération méthodes: {str(e)}"
        )


@router.post("/payment-methods")
async def add_payment_method(
    payment_method_id: str,
    set_as_default: bool = True,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    ➕ Ajoute une méthode de paiement
    """
    try:
        subscription = await fetch_user_subscription(current_user.id)
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aucun abonnement actif"
            )
        
        # Attacher la méthode au customer
        stripe.PaymentMethod.attach(
            payment_method_id,
            customer=subscription.stripe_customer_id
        )
        
        # Définir comme défaut si demandé
        if set_as_default:
            stripe.Customer.modify(
                subscription.stripe_customer_id,
                invoice_settings={
                    'default_payment_method': payment_method_id
                }
            )
        
        return {
            "message": "Méthode de paiement ajoutée avec succès",
            "payment_method_id": payment_method_id,
            "is_default": set_as_default
        }
    
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur Stripe: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur ajout méthode: {str(e)}"
        )


@router.delete("/payment-methods/{payment_method_id}")
async def delete_payment_method(
    payment_method_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    🗑️ Supprime une méthode de paiement
    """
    try:
        # Détacher la méthode
        stripe.PaymentMethod.detach(payment_method_id)
        
        return {
            "message": "Méthode de paiement supprimée",
            "payment_method_id": payment_method_id
        }
    
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur Stripe: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur suppression: {str(e)}"
        )


# ============================================
# ROUTES - INVOICES
# ============================================

@router.get("/invoices", response_model=List[Invoice])
async def list_invoices(
    limit: int = 10,
    current_user: User = Depends(get_current_user)
) -> List[Invoice]:
    """
    🧾 Liste les factures
    """
    try:
        subscription = await fetch_user_subscription(current_user.id)
        
        if not subscription or not subscription.stripe_customer_id:
            return []
        
        # Récupérer les invoices depuis Stripe
        invoices = stripe.Invoice.list(
            customer=subscription.stripe_customer_id,
            limit=limit
        )
        
        invoice_list = []
        for inv in invoices.data:
            invoice_list.append(Invoice(
                id=inv.id,
                user_id=current_user.id,
                amount=inv.amount_paid / 100,  # Stripe utilise cents
                currency=inv.currency.upper(),
                status=inv.status,
                invoice_pdf=inv.invoice_pdf,
                invoice_number=inv.number,
                billing_reason=inv.billing_reason,
                created_at=datetime.fromtimestamp(inv.created),
                paid_at=datetime.fromtimestamp(inv.status_transitions.paid_at) if inv.status_transitions.paid_at else None
            ))
        
        return invoice_list
    
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur Stripe: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur récupération factures: {str(e)}"
        )


@router.get("/invoices/{invoice_id}", response_model=Invoice)
async def get_invoice_details(
    invoice_id: str,
    current_user: User = Depends(get_current_user)
) -> Invoice:
    """
    🔍 Détails d'une facture
    """
    try:
        inv = stripe.Invoice.retrieve(invoice_id)
        
        # Vérifier que la facture appartient à l'utilisateur
        subscription = await fetch_user_subscription(current_user.id)
        if inv.customer != subscription.stripe_customer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès interdit"
            )
        
        return Invoice(
            id=inv.id,
            user_id=current_user.id,
            amount=inv.amount_paid / 100,
            currency=inv.currency.upper(),
            status=inv.status,
            invoice_pdf=inv.invoice_pdf,
            invoice_number=inv.number,
            billing_reason=inv.billing_reason,
            created_at=datetime.fromtimestamp(inv.created),
            paid_at=datetime.fromtimestamp(inv.status_transitions.paid_at) if inv.status_transitions.paid_at else None
        )
    
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur Stripe: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur récupération facture: {str(e)}"
        )


# ============================================
# WEBHOOKS STRIPE
# ============================================

@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    🔔 Webhook Stripe pour les événements
    
    **Gère:**
    - checkout.session.completed
    - customer.subscription.updated
    - customer.subscription.deleted
    - invoice.payment_succeeded
    - invoice.payment_failed
    """
    try:
        payload = await request.body()
        sig_header = request.headers.get('stripe-signature')
        
        # Vérifier la signature
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid signature")
        
        # Gérer les événements
        if event['type'] == 'checkout.session.completed':
            await handle_checkout_completed(event['data']['object'])
        
        elif event['type'] == 'customer.subscription.updated':
            await handle_subscription_updated(event['data']['object'])
        
        elif event['type'] == 'customer.subscription.deleted':
            await handle_subscription_deleted(event['data']['object'])
        
        elif event['type'] == 'invoice.payment_succeeded':
            await handle_payment_succeeded(event['data']['object'])
        
        elif event['type'] == 'invoice.payment_failed':
            await handle_payment_failed(event['data']['object'])
        
        return {"status": "success"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur webhook: {str(e)}"
        )


# ============================================
# HELPER FUNCTIONS
# ============================================

async def get_or_create_stripe_customer(user: User):
    """Récupère ou crée un customer Stripe"""
    # TODO: Vérifier si existe en DB
    existing = await get_stripe_customer_id(user.id)
    
    if existing:
        return stripe.Customer.retrieve(existing)
    
    # Créer nouveau customer
    customer = stripe.Customer.create(
        email=user.email,
        name=f"{user.first_name} {user.last_name}",
        metadata={
            'user_id': str(user.id)
        }
    )
    
    # Sauvegarder l'ID
    await save_stripe_customer_id(user.id, customer.id)
    
    return customer


async def fetch_user_subscription(user_id: uuid.UUID):
    """Récupère l'abonnement d'un utilisateur"""
    # TODO: DB query
    return None


async def change_subscription_plan(user_id, stripe_sub_id, new_plan_id, billing_cycle):
    """Change de plan d'abonnement"""
    # TODO: Stripe modification
    pass


async def update_auto_renew(stripe_sub_id, auto_renew):
    """Met à jour le renouvellement automatique"""
    stripe.Subscription.modify(
        stripe_sub_id,
        cancel_at_period_end=not auto_renew
    )


async def update_subscription_status(sub_id, status, end_date):
    """Met à jour le statut d'abonnement"""
    # TODO: DB update
    pass


async def get_stripe_customer_id(user_id):
    """Récupère l'ID customer Stripe"""
    # TODO: DB query
    return None


async def save_stripe_customer_id(user_id, customer_id):
    """Sauvegarde l'ID customer Stripe"""
    # TODO: DB save
    pass


# Webhook handlers
async def handle_checkout_completed(session):
    """Gère la fin du checkout"""
    user_id = session['metadata']['user_id']
    # TODO: Créer l'abonnement en DB
    pass


async def handle_subscription_updated(subscription):
    """Gère la mise à jour d'abonnement"""
    # TODO: Mettre à jour en DB
    pass


async def handle_subscription_deleted(subscription):
    """Gère la suppression d'abonnement"""
    # TODO: Marquer comme annulé en DB
    pass


async def handle_payment_succeeded(invoice):
    """Gère le paiement réussi"""
    # TODO: Enregistrer la facture
    pass


async def handle_payment_failed(invoice):
    """Gère l'échec de paiement"""
    # TODO: Notifier l'utilisateur
    pass
