"""
Memory layer for the Agentic Outreach system.

Current backend: In-process Python dictionaries (lost on restart)
Future backend:  Redis, PostgreSQL, or any persistent store

To swap backends later:
- Keep the MemoryService interface exactly as is
- Replace the contents of ProspectMemoryBackend, LearningMemoryBackend, OfferMemoryBackend
- Nothing else in the codebase needs to change
"""

import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

# ----------------------------
# MEMORY SCHEMAS
# These define what gets stored, not where
# ----------------------------

class ProspectMemoryRecord(BaseModel):
    """Everything we know about a prospect across all runs"""
    prospect_id: str                          # Usually name+company slugified
    name: str
    company: str
    role: Optional[str] = None
    
    # Contact history
    times_contacted: int = 0
    last_contacted_at: Optional[str] = None
    last_channel_used: Optional[str] = None
    last_stage_used: Optional[str] = None
    last_message_sent: Optional[str] = None
    
    # Response tracking
    ever_replied: bool = False
    reply_sentiment: Optional[str] = None    # positive, negative, neutral
    
    # What we've tried
    hooks_used: List[str] = []               # So we don't repeat the same hook
    angles_tried: List[str] = []             # So we don't repeat the same angle
    offers_pitched: List[str] = []           # Which offers have been shown
    
    # Notes
    do_not_contact: bool = False
    notes: Optional[str] = None
    
    # Timestamps
    first_seen_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class LearningMemoryRecord(BaseModel):
    """
    Aggregate learning across all runs.
    Gets smarter the more the system is used.
    """
    # Hook performance
    best_performing_hooks: List[str] = []    # Hooks that led to replies
    worst_performing_hooks: List[str] = []   # Hooks that got no response
    
    # Angle performance
    best_performing_angles: List[str] = []
    worst_performing_angles: List[str] = []
    
    # Channel performance
    channel_reply_rates: Dict[str, float] = {}   # e.g. {"linkedin_dm": 0.23, "email": 0.11}
    
    # Stage performance
    stage_reply_rates: Dict[str, float] = {}     # e.g. {"first_touch": 0.15}
    
    # Template performance
    template_reply_rates: Dict[str, float] = {}  # e.g. {"soft_sell": 0.20}
    
    # Overall stats
    total_messages_generated: int = 0
    total_messages_sent: int = 0             # future, when send is implemented
    total_replies_received: int = 0          # future, when tracking is implemented
    avg_quality_score: float = 0.0
    
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class OfferMemoryRecord(BaseModel):
    """
    Performance data per offer.
    Tracks which offers resonate with which types of prospects.
    """
    offer_id: str
    offer_name: str
    
    # Performance
    times_used: int = 0
    times_replied: int = 0                   # future
    avg_quality_score: float = 0.0
    
    # What works with this offer
    best_channels: List[str] = []
    best_angles: List[str] = []
    best_prospect_roles: List[str] = []
    
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# ----------------------------
# BACKEND: PLACEHOLDER (IN-MEMORY)
# Replace this entire section with Redis/Postgres later
# The interface (method names and signatures) must stay the same
# ----------------------------

class _InMemoryStore:
    """
    Temporary in-process store.
    Data lives as long as the server process lives.
    Restart the server = all memory gone.
    
    REPLACE WITH REDIS:
        client = redis.Redis(host=..., port=..., db=0)
        client.set(key, json.dumps(value))
        client.get(key)
        client.expire(key, ttl_seconds)
    
    REPLACE WITH POSTGRES:
        Use SQLAlchemy or asyncpg
        Store JSON blobs in a jsonb column
    """
    
    def __init__(self):
        self._store: Dict[str, str] = {}
    
    def set(self, key: str, value: dict) -> None:
        self._store[key] = json.dumps(value, default=str)
    
    def get(self, key: str) -> Optional[dict]:
        raw = self._store.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    
    def delete(self, key: str) -> None:
        self._store.pop(key, None)
    
    def exists(self, key: str) -> bool:
        return key in self._store
    
    def keys_with_prefix(self, prefix: str) -> List[str]:
        return [k for k in self._store.keys() if k.startswith(prefix)]


# Singleton store instance
# When you swap to Redis, replace this one line:
# _store = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)
_store = _InMemoryStore()


# ----------------------------
# MEMORY SERVICE
# This is what the rest of the app uses
# Never import _store or _InMemoryStore directly outside this file
# ----------------------------

class ProspectMemoryService:
    """Read and write prospect memory"""
    
    @staticmethod
    def _make_key(name: str, company: str) -> str:
        """Consistent key format for prospect lookup"""
        slug_name = name.lower().replace(" ", "_")
        slug_company = company.lower().replace(" ", "_")
        return f"prospect:{slug_name}:{slug_company}"
    
    @staticmethod
    def get(name: str, company: str) -> Optional[ProspectMemoryRecord]:
        """
        Fetch prospect memory.
        Returns None if prospect has never been seen before.
        """
        key = ProspectMemoryService._make_key(name, company)
        data = _store.get(key)
        if data is None:
            return None
        return ProspectMemoryRecord(**data)
    
    @staticmethod
    def save(record: ProspectMemoryRecord) -> None:
        """Save or update prospect memory"""
        key = ProspectMemoryService._make_key(record.name, record.company)
        record.updated_at = datetime.now().isoformat()
        _store.set(key, record.model_dump())
    
    @staticmethod
    def get_or_create(name: str, company: str, role: Optional[str] = None) -> ProspectMemoryRecord:
        """
        Fetch if exists, create fresh record if not.
        This is what agents should call.
        """
        existing = ProspectMemoryService.get(name, company)
        if existing:
            return existing
        
        slug_name = name.lower().replace(" ", "_")
        slug_company = company.lower().replace(" ", "_")
        
        return ProspectMemoryRecord(
            prospect_id=f"{slug_name}:{slug_company}",
            name=name,
            company=company,
            role=role
        )
    
    @staticmethod
    def record_outreach(
        name: str,
        company: str,
        channel: str,
        stage: str,
        hook_used: str,
        angle_used: str,
        offer_name: str,
        message_sent: str
    ) -> None:
        """
        Call this after a message is generated/sent.
        Updates all the tracking fields.
        """
        record = ProspectMemoryService.get_or_create(name, company)
        
        record.times_contacted += 1
        record.last_contacted_at = datetime.now().isoformat()
        record.last_channel_used = channel
        record.last_stage_used = stage
        record.last_message_sent = message_sent
        
        if hook_used and hook_used not in record.hooks_used:
            record.hooks_used.append(hook_used)
        
        if angle_used and angle_used not in record.angles_tried:
            record.angles_tried.append(angle_used)
        
        if offer_name and offer_name not in record.offers_pitched:
            record.offers_pitched.append(offer_name)
        
        ProspectMemoryService.save(record)
    
    @staticmethod
    def mark_replied(name: str, company: str, sentiment: str = "positive") -> None:
        """Call this when a prospect replies (future feature)"""
        record = ProspectMemoryService.get_or_create(name, company)
        record.ever_replied = True
        record.reply_sentiment = sentiment
        ProspectMemoryService.save(record)
    
    @staticmethod
    def mark_do_not_contact(name: str, company: str) -> None:
        """Mark a prospect as do not contact"""
        record = ProspectMemoryService.get_or_create(name, company)
        record.do_not_contact = True
        ProspectMemoryService.save(record)


class LearningMemoryService:
    """Read and write system-wide learning memory"""
    
    GLOBAL_KEY = "learning:global"
    
    @staticmethod
    def get() -> LearningMemoryRecord:
        """Get global learning record, create if not exists"""
        data = _store.get(LearningMemoryService.GLOBAL_KEY)
        if data is None:
            return LearningMemoryRecord()
        return LearningMemoryRecord(**data)
    
    @staticmethod
    def save(record: LearningMemoryRecord) -> None:
        """Save global learning record"""
        record.updated_at = datetime.now().isoformat()
        _store.set(LearningMemoryService.GLOBAL_KEY, record.model_dump())
    
    @staticmethod
    def record_generation(quality_score: int, channel: str, stage: str, template: str) -> None:
        """
        Call this after every successful generation.
        Tracks aggregate stats.
        """
        record = LearningMemoryService.get()
        
        record.total_messages_generated += 1
        
        # Rolling average quality score
        total = record.total_messages_generated
        record.avg_quality_score = (
            (record.avg_quality_score * (total - 1) + quality_score) / total
        )
        
        # Initialize channel/stage/template rates if first time seen
        if channel not in record.channel_reply_rates:
            record.channel_reply_rates[channel] = 0.0
        
        if stage not in record.stage_reply_rates:
            record.stage_reply_rates[stage] = 0.0
        
        if template not in record.template_reply_rates:
            record.template_reply_rates[template] = 0.0
        
        LearningMemoryService.save(record)
    
    @staticmethod
    def record_successful_hook(hook: str) -> None:
        """Call when a hook leads to a reply"""
        record = LearningMemoryService.get()
        if hook not in record.best_performing_hooks:
            record.best_performing_hooks.append(hook)
        if hook in record.worst_performing_hooks:
            record.worst_performing_hooks.remove(hook)
        LearningMemoryService.save(record)
    
    @staticmethod
    def record_failed_hook(hook: str) -> None:
        """Call when a hook gets no response"""
        record = LearningMemoryService.get()
        if hook not in record.worst_performing_hooks:
            record.worst_performing_hooks.append(hook)
        LearningMemoryService.save(record)


class OfferMemoryService:
    """Read and write per-offer performance memory"""
    
    @staticmethod
    def _make_key(offer_name: str) -> str:
        slug = offer_name.lower().replace(" ", "_")
        return f"offer:{slug}"
    
    @staticmethod
    def get(offer_name: str) -> Optional[OfferMemoryRecord]:
        key = OfferMemoryService._make_key(offer_name)
        data = _store.get(key)
        if data is None:
            return None
        return OfferMemoryRecord(**data)
    
    @staticmethod
    def get_or_create(offer_name: str) -> OfferMemoryRecord:
        existing = OfferMemoryService.get(offer_name)
        if existing:
            return existing
        slug = offer_name.lower().replace(" ", "_")
        return OfferMemoryRecord(
            offer_id=slug,
            offer_name=offer_name
        )
    
    @staticmethod
    def save(record: OfferMemoryRecord) -> None:
        key = OfferMemoryService._make_key(record.offer_name)
        record.updated_at = datetime.now().isoformat()
        _store.set(key, record.model_dump())
    
    @staticmethod
    def record_usage(
        offer_name: str,
        channel: str,
        angle: str,
        prospect_role: Optional[str],
        quality_score: int
    ) -> None:
        """Call every time an offer is used in a generation"""
        record = OfferMemoryService.get_or_create(offer_name)
        
        record.times_used += 1
        
        # Rolling average score
        record.avg_quality_score = (
            (record.avg_quality_score * (record.times_used - 1) + quality_score) 
            / record.times_used
        )
        
        if channel and channel not in record.best_channels:
            record.best_channels.append(channel)
        
        if angle and angle not in record.best_angles:
            record.best_angles.append(angle)
        
        if prospect_role and prospect_role not in record.best_prospect_roles:
            record.best_prospect_roles.append(prospect_role)
        
        OfferMemoryService.save(record)


# ----------------------------
# SINGLE IMPORT POINT
# Everything outside this file imports from here
# ----------------------------

class MemoryService:
    """
    Unified access point for all memory operations.
    
    Usage:
        from .memory import MemoryService
        
        prospect = MemoryService.prospects.get_or_create("Sarah Chen", "Ramp")
        MemoryService.learning.record_generation(score=91, channel="linkedin_dm", ...)
        MemoryService.offers.record_usage(offer_name="SDR Audit", ...)
    """
    prospects = ProspectMemoryService
    learning = LearningMemoryService
    offers = OfferMemoryService