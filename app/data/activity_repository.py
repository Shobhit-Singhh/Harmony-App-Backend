# app/data/activity_repository.py
from enum import Enum
from typing import Dict, List, Any


# =====================================================================
# ENUMS
# =====================================================================

class PillarType(str, Enum):
    """Four pillars of wellbeing."""
    HEALTH = "health"
    WORK = "work"
    GROWTH = "growth"
    RELATIONSHIPS = "relationships"


# =====================================================================
# ACTIVITY TEMPLATE REPOSITORY
# =====================================================================

ACTIVITY_REPOSITORY: List[Dict[str, Any]] = [
    # HEALTH PILLAR
    {"name": "Walking", "description": "Daily walking for physical health", "pillars": [PillarType.HEALTH]},
    {"name": "Running", "description": "Cardiovascular exercise", "pillars": [PillarType.HEALTH]},
    {"name": "Gym Workout", "description": "Strength and fitness training", "pillars": [PillarType.HEALTH]},
    {"name": "Yoga", "description": "Physical and mental wellness", "pillars": [PillarType.HEALTH, PillarType.GROWTH]},
    {"name": "Cycling", "description": "Low-impact cardio exercise", "pillars": [PillarType.HEALTH]},
    {"name": "Swimming", "description": "Full-body workout", "pillars": [PillarType.HEALTH]},
    {"name": "Water Intake", "description": "Daily hydration tracking", "pillars": [PillarType.HEALTH]},
    {"name": "Sleep", "description": "Quality sleep tracking", "pillars": [PillarType.HEALTH]},
    
    # WORK PILLAR
    {"name": "Upskilling", "description": "Learning new professional skills", "pillars": [PillarType.WORK, PillarType.GROWTH]},
    {"name": "Deep Work Sessions", "description": "Focused, uninterrupted work", "pillars": [PillarType.WORK]},
    {"name": "Professional Networking", "description": "Building professional relationships", "pillars": [PillarType.WORK, PillarType.RELATIONSHIPS]},
    {"name": "Productive Meetings", "description": "Effective collaboration sessions", "pillars": [PillarType.WORK]},
    {"name": "Side Project", "description": "Personal project development", "pillars": [PillarType.WORK, PillarType.GROWTH]},
    
    # GROWTH PILLAR
    {"name": "Meditation", "description": "Mindfulness and mental clarity", "pillars": [PillarType.GROWTH]},
    {"name": "Reading", "description": "Personal development through books", "pillars": [PillarType.GROWTH]},
    {"name": "Journaling", "description": "Self-reflection and writing", "pillars": [PillarType.GROWTH]},
    {"name": "Language Learning", "description": "Learning a new language", "pillars": [PillarType.GROWTH]},
    {"name": "Creative Hobby", "description": "Artistic or creative pursuits", "pillars": [PillarType.GROWTH]},
    {"name": "Podcasts/Audiobooks", "description": "Learning through audio content", "pillars": [PillarType.GROWTH]},
    
    # RELATIONSHIPS PILLAR
    {"name": "Social Gatherings", "description": "Meeting with friends and family", "pillars": [PillarType.RELATIONSHIPS]},
    {"name": "Quality Family Time", "description": "Dedicated time with family", "pillars": [PillarType.RELATIONSHIPS]},
    {"name": "Video/Phone Calls", "description": "Stay connected remotely", "pillars": [PillarType.RELATIONSHIPS]},
    {"name": "Date Night", "description": "Quality time with partner", "pillars": [PillarType.RELATIONSHIPS]},
    {"name": "Community Volunteering", "description": "Giving back to community", "pillars": [PillarType.RELATIONSHIPS]},
    {"name": "Check-in Messages", "description": "Reaching out to loved ones", "pillars": [PillarType.RELATIONSHIPS]},
    {"name": "Mentoring", "description": "Guiding and supporting others", "pillars": [PillarType.RELATIONSHIPS, PillarType.GROWTH]}
]