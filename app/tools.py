import random
from typing import List, Dict, Any
from datetime import datetime, timedelta
from .models import Signal  # CHANGED: removed ProspectMemory, OfferMemory, they no longer exist in models.py
from .config import settings
import httpx

class ResearchTools:
    """Research tools with real API support and mock fallback"""
    
    @staticmethod
    def fetch_linkedin_posts(name: str, company: str) -> List[Signal]:
        """Fetch LinkedIn posts (mock for now, ready for real API)"""
        
        if not settings.USE_MOCK_DATA and settings.LINKEDIN_API_KEY:
            # TODO: Implement real LinkedIn API call
            # return ResearchTools._fetch_linkedin_real(name, company)
            pass
        
        # Mock data with more variety
        mock_posts = [
            {
                "content": f"Just hit a major milestone at {company} - our team doubled revenue this quarter through a new SDR pod approach.",
                "strength": "high",
                "timestamp": (datetime.now() - timedelta(days=2)).isoformat()
            },
            {
                "content": f"Excited to share that {company} is hiring! Looking for talented folks who want to scale with us.",
                "strength": "medium",
                "timestamp": (datetime.now() - timedelta(days=5)).isoformat()
            },
            {
                "content": "Really interesting article about AI in sales. The future is here.",
                "strength": "low",
                "timestamp": (datetime.now() - timedelta(days=10)).isoformat()
            }
        ]
        
        # Return 1-2 random posts
        selected = random.sample(mock_posts, k=random.randint(1, 2))
        
        return [
            Signal(
                type="linkedin_post",
                content=post["content"],
                strength=post["strength"],
                timestamp=post["timestamp"],
                source_url=f"https://linkedin.com/posts/{name.lower().replace(' ', '-')}-{random.randint(1000, 9999)}",
                why_relevant="Recent professional activity showing current priorities and interests"
            )
            for post in selected
        ]
    
    @staticmethod
    def fetch_company_news(company: str) -> List[Signal]:
        """Fetch company news (mock for now, ready for real API)"""
        
        if not settings.USE_MOCK_DATA and settings.NEWS_API_KEY:
            # TODO: Implement real News API call
            # return ResearchTools._fetch_news_real(company)
            pass
        
        # Mock news with variety
        mock_news = [
            {
                "content": f"{company} announces new AI-powered product features to streamline customer workflows",
                "strength": "high",
                "timestamp": (datetime.now() - timedelta(days=1)).isoformat()
            },
            {
                "content": f"{company} raises Series B funding to expand into European markets",
                "strength": "medium",
                "timestamp": (datetime.now() - timedelta(days=7)).isoformat()
            },
            {
                "content": f"{company} named one of the fastest-growing companies in their sector",
                "strength": "medium",
                "timestamp": (datetime.now() - timedelta(days=14)).isoformat()
            }
        ]
        
        # Return 1 random news item
        selected = random.choice(mock_news)
        
        return [
            Signal(
                type="company_news",
                content=selected["content"],
                strength=selected["strength"],
                timestamp=selected["timestamp"],
                source_url=f"https://techcrunch.com/2024/01/15/{company.lower()}-news",
                why_relevant="Recent company developments showing growth trajectory and strategic focus"
            )
        ]
    
    @staticmethod
    def get_crm_history(name: str) -> Dict[str, Any]:
        """Get CRM history (mock for now, ready for real DB)"""
        
        if not settings.USE_MOCK_DATA and settings.CRM_DATABASE_URL:
            # TODO: Implement real CRM database query
            # return ResearchTools._fetch_crm_real(name)
            pass
        
        # Mock CRM data
        has_history = random.random() > 0.7  # 30% chance of past contact
        
        return {
            "past_contact": has_history,
            "last_contact_date": (datetime.now() - timedelta(days=random.randint(30, 180))).isoformat() if has_history else None,
            "last_seen_topic": "product demo" if has_history else None,
            "replied_before": has_history and random.random() > 0.5,
            "engagement_score": random.randint(1, 10) if has_history else 0
        }

class ReasoningTools:
    """Tools that help the agent reason or score - mostly deprecated in favor of LLM"""
    
    @staticmethod
    def score_hook_relevance(hook: str, persona: str) -> int:
        """Simple scoring - now mostly handled by LLM"""
        score = 70
        
        if any(word in hook.lower() for word in ["just", "today", "yesterday", "announced"]):
            score += 10  # Timely
        
        if any(word in hook.lower() for word in ["milestone", "launched", "raised", "hired"]):
            score += 10  # Significant event
        
        return min(score, 95)
    
    @staticmethod
    def detect_placeholder_text(message: str) -> bool:
        """Detect unfilled placeholder tokens like [Company], [Name], [Result], etc."""
        import re
        return bool(re.search(r'\[.{1,40}\]', message))

    @staticmethod
    def detect_overpersonalization(message: str) -> bool:
        """Enhanced creepiness detection"""
        creepy_phrases = [
            "i saw your house",
            "i know where you live",
            "i noticed your kids",
            "i saw your family",
            "i know your address",
            "i've been watching",
            "i followed you",
            "stalking your profile"
        ]
        message_lower = message.lower()
        return any(phrase in message_lower for phrase in creepy_phrases)