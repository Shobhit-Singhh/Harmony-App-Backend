from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import date, datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app import models, schemas
from app.crud.user_daily_log import crud_user_daily_log
from app.crud.user_priorities import crud_user_priorities


class PrioritiesNotFoundError(Exception):
    """Raised when the user has no activity priorities set."""
    pass


class UserDailyLogService:
    """
    Complete service layer for User Daily Log operations.
    """

    # ====================================================
    # HELPER METHODS FOR ACTIVITIES
    # ====================================================

    def get_all_user_activities(
        self, db: Session, user_id: UUID
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get all activities across all pillars from user priorities."""
        priorities = crud_user_priorities.get_by_user_id(db, user_id=user_id)
        if not priorities:
            raise PrioritiesNotFoundError("User has no priorities set")

        return crud_user_priorities.get_all_activities(priorities)

    def _reset_activity_complete_values(
        self, activities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Reset complete values to 0 for all activities."""
        if not activities:
            return []
        
        reset_activities = []
        for activity in activities:
            # Deep copy to avoid mutating original
            activity_copy = {
                "name": activity.get("name"),
                "description": activity.get("description"),
                "pillar": activity.get("pillar"),
                "configuration": {}
            }
            
            # Copy configuration and reset complete
            if "configuration" in activity:
                config = activity["configuration"].copy()
                config["complete"] = 0
                activity_copy["configuration"] = config
            else:
                activity_copy["configuration"] = {"complete": 0}
            
            reset_activities.append(activity_copy)
        
        return reset_activities

    def _has_activities(self, tracker: models.UserActivityTracker) -> bool:
        """Check if tracker has any activities populated."""
        return any([
            tracker.health_activity,
            tracker.work_activity,
            tracker.growth_activity,
            tracker.relationship_activity
        ])

    # ====================================================
    # DAILY LOG MANAGEMENT
    # ====================================================

    def get_or_create_daily_log(
        self, db: Session, *, user_id: UUID, log_date: date
    ) -> models.UserDailyLog:
        """Get existing daily log or create a new one with activities from priorities."""
        daily_log = crud_user_daily_log.get_by_user_and_date(
            db=db, user_id=user_id, day=log_date
        )

        if daily_log:
            return daily_log

        # Get all user activities from priorities
        try:
            all_activities = self.get_all_user_activities(db=db, user_id=user_id)
            
            # Reset complete values to 0 for new day
            activities_data = schemas.UserActivityTrackerBase(
                health_activity=self._reset_activity_complete_values(
                    all_activities.get("health", [])
                ),
                work_activity=self._reset_activity_complete_values(
                    all_activities.get("work", [])
                ),
                growth_activity=self._reset_activity_complete_values(
                    all_activities.get("growth", [])
                ),
                relationship_activity=self._reset_activity_complete_values(
                    all_activities.get("relationships", [])
                ),
                # Coping activities remain empty by default
                health_coping=[],
                productivity_coping=[],
                mindfulness_coping=[],
                relationship_coping=[]
            )
            
            create_data = schemas.UserDailyLogCreate(
                user_id=user_id,
                date=log_date,
                frequency={},
                active_hours={},
                activities=activities_data
            )
        except PrioritiesNotFoundError:
            # If no priorities found, create with empty activities
            create_data = schemas.UserDailyLogCreate(
                user_id=user_id,
                date=log_date,
                frequency={},
                active_hours={}
            )

        # Use custom create method that handles nested activities
        return crud_user_daily_log.create_with_activities(db=db, obj_in=create_data)

    def get_daily_log_with_details(
        self, db: Session, *, user_id: UUID, log_date: date
    ) -> Optional[Dict[str, Any]]:
        """Get complete daily log with all related data."""
        daily_log = crud_user_daily_log.get_by_user_and_date(
            db=db, user_id=user_id, day=log_date
        )

        if not daily_log:
            return None

        checkin = crud_user_daily_log.get_checkin(db=db, log_id=daily_log.id)
        journal = crud_user_daily_log.get_journal(db=db, log_id=daily_log.id)
        chatbot = crud_user_daily_log.get_chatbot_log(db=db, log_id=daily_log.id)
        activities = crud_user_daily_log.get_activities(db=db, log_id=daily_log.id)

        return {
            "id": daily_log.id,
            "user_id": daily_log.user_id,
            "date": daily_log.date,
            "current_status_summary": daily_log.current_status_summary,
            "frequency": daily_log.frequency,
            "active_hours": daily_log.active_hours,
            "created_at": daily_log.created_at,
            "checkin": {
                "mood": checkin.mood if checkin else {},
                "stress_level": checkin.stress_level if checkin else {},
                "energy_level": checkin.energy_level if checkin else {},
                "sleep": checkin.sleep if checkin else {},
            },
            "journal": {
                "entries": journal.journal if journal else {},
                "analysis": journal.analysis if journal else {},
            },
            "chatbot": {
                "conversation": chatbot.conversation if chatbot else [],
                "analysis": chatbot.analysis if chatbot else {},
            },
            "activities": {
                "health_activity": activities.health_activity if activities else [],
                "work_activity": activities.work_activity if activities else [],
                "growth_activity": activities.growth_activity if activities else [],
                "relationship_activity": activities.relationship_activity if activities else [],
                "health_coping": activities.health_coping if activities else [],
                "productivity_coping": activities.productivity_coping if activities else [],
                "mindfulness_coping": activities.mindfulness_coping if activities else [],
                "relationship_coping": activities.relationship_coping if activities else [],
            },
        }

    def get_date_range_logs(
        self, db: Session, *, user_id: UUID, start_date: date, end_date: date
    ) -> List[Dict[str, Any]]:
        """Get all daily logs within a date range."""
        logs = crud_user_daily_log.get_by_date_range(
            db=db, user_id=user_id, start_date=start_date, end_date=end_date
        )

        result = []
        for log in logs:
            activities = crud_user_daily_log.get_activities(db=db, log_id=log.id)
            checkin = crud_user_daily_log.get_checkin(db=db, log_id=log.id)

            result.append(
                {
                    "id": log.id,
                    "date": log.date,
                    "summary": log.current_status_summary,
                    "has_checkin": bool(checkin and checkin.mood),
                    "activity_count": (
                        sum(
                            [
                                len(activities.health_activity or []),
                                len(activities.work_activity or []),
                                len(activities.growth_activity or []),
                                len(activities.relationship_activity or []),
                            ]
                        )
                        if activities
                        else 0
                    ),
                }
            )

        return result

    # ====================================================
    # CHECKIN OPERATIONS
    # ====================================================

    def add_checkin_entry(
        self,
        db: Session,
        *,
        user_id: UUID,
        log_date: date,
        field: str,
        timestamp: datetime,
        value: Any,
    ) -> models.UserCheckin:
        """Add a NEW checkin entry with timestamp."""
        daily_log = self.get_or_create_daily_log(
            db=db, user_id=user_id, log_date=log_date
        )

        checkin = crud_user_daily_log.get_checkin(db=db, log_id=daily_log.id)

        if not checkin:
            raise ValueError("Checkin record not found")

        timestamp_str = timestamp.isoformat() if isinstance(timestamp, datetime) else str(timestamp)
        current_field_data = getattr(checkin, field, {}) or {}

        if timestamp_str in current_field_data:
            raise ValueError(
                f"Entry with timestamp {timestamp_str} already exists. Use update instead."
            )

        current_field_data[timestamp_str] = value
        setattr(checkin, field, current_field_data)
        flag_modified(checkin, field)

        db.commit()
        db.refresh(checkin)
        return checkin

    def update_checkin_entry(
        self,
        db: Session,
        *,
        user_id: UUID,
        log_date: date,
        field: str,
        timestamp: datetime,
        value: Any,
    ) -> models.UserCheckin:
        """Update an EXISTING checkin entry."""
        daily_log = self.get_or_create_daily_log(
            db=db, user_id=user_id, log_date=log_date
        )

        checkin = crud_user_daily_log.get_checkin(db=db, log_id=daily_log.id)

        if not checkin:
            raise ValueError("Checkin record not found")

        timestamp_str = timestamp.isoformat() if isinstance(timestamp, datetime) else str(timestamp)
        current_field_data = getattr(checkin, field, {}) or {}

        if timestamp_str not in current_field_data:
            raise ValueError(
                f"Timestamp {timestamp_str} not found. Use add instead."
            )

        current_field_data[timestamp_str] = value
        setattr(checkin, field, current_field_data)
        flag_modified(checkin, field)

        db.commit()
        db.refresh(checkin)
        return checkin

    def get_latest_checkin_values(
        self, db: Session, *, user_id: UUID, log_date: date
    ) -> Dict[str, Any]:
        """Get the most recent values for all checkin fields."""
        checkin = crud_user_daily_log.get_checkin_by_user_and_date(
            db=db, user_id=user_id, day=log_date
        )

        if not checkin:
            return {
                "mood": None,
                "stress_level": None,
                "energy_level": None,
                "sleep": None,
            }

        def get_latest_value(data_dict: Dict) -> Any:
            if not data_dict:
                return None
            latest_key = max(data_dict.keys())
            return data_dict[latest_key]

        return {
            "mood": get_latest_value(checkin.mood),
            "stress_level": get_latest_value(checkin.stress_level),
            "energy_level": get_latest_value(checkin.energy_level),
            "sleep": get_latest_value(checkin.sleep),
        }

    def get_full_day_checkin_history(
        self, db: Session, *, user_id: UUID, log_date: date
    ) -> Dict[str, Any]:
        """Return complete check-in history for the given date."""
        checkin = crud_user_daily_log.get_checkin_by_user_and_date(
            db=db, user_id=user_id, day=log_date
        )

        if not checkin:
            return {
                "mood": {},
                "stress_level": {},
                "energy_level": {},
                "sleep": {},
            }

        return {
            "mood": checkin.mood or {},
            "stress_level": checkin.stress_level or {},
            "energy_level": checkin.energy_level or {},
            "sleep": checkin.sleep or {},
        }

    # ====================================================
    # JOURNAL OPERATIONS
    # ====================================================

    def add_journal_entry(
        self,
        db: Session,
        *,
        user_id: UUID,
        log_date: date,
        content: str,
        entry_type: str = "text",
        sentiment: Optional[str] = None,
        topics: Optional[List[str]] = None,
        timestamp: datetime,
    ) -> models.UserJournal:
        """Add a journal entry."""
        daily_log = self.get_or_create_daily_log(
            db=db, user_id=user_id, log_date=log_date
        )

        return crud_user_daily_log.add_journal_entry(
            db=db,
            log_id=daily_log.id,
            timestamp=timestamp,
            entry_type=entry_type,
            content=content,
            sentiment=sentiment,
            topics=topics,
        )

    def update_journal_entry(
        self,
        db: Session,
        *,
        user_id: UUID,
        log_date: date,
        timestamp: datetime,
        content: Optional[str] = None,
        entry_type: Optional[str] = None,
        sentiment: Optional[str] = None,
        topics: Optional[List[str]] = None,
    ) -> models.UserJournal:
        """Update an existing journal entry."""
        daily_log = self.get_or_create_daily_log(
            db=db, user_id=user_id, log_date=log_date
        )

        journal = crud_user_daily_log.get_journal(db, log_id=daily_log.id)
        if not journal:
            raise ValueError("Journal not found")

        return crud_user_daily_log.update_journal_entry(
            db=db,
            log_id=daily_log.id,
            timestamp=timestamp,
            entry_type=entry_type,
            content=content,
            sentiment=sentiment,
            topics=topics,
        )

    def get_journal_entries(
        self, db: Session, *, user_id: UUID, log_date: date
    ) -> Dict[str, List[Any]]:
        """Get all journal entries for a date."""
        journal = crud_user_daily_log.get_journal_by_user_and_date(
            db=db, user_id=user_id, day=log_date
        )
        return journal.journal if journal and journal.journal else {}

    def delete_journal_entry(
        self, db: Session, *, user_id: UUID, log_date: date, timestamp: datetime
    ) -> bool:
        """Delete a journal entry."""
        daily_log = self.get_or_create_daily_log(
            db=db, user_id=user_id, log_date=log_date
        )
        return crud_user_daily_log.delete_journal_entry(
            db=db, log_id=daily_log.id, timestamp=timestamp
        )

    # ====================================================
    # CHATBOT OPERATIONS
    # ====================================================

    def add_chatbot_message(
        self, db: Session, *, user_id: UUID, log_date: date, role: str, content: str
    ) -> models.UserChatbotLog:
        """Add a message to chatbot conversation."""
        daily_log = self.get_or_create_daily_log(
            db=db, user_id=user_id, log_date=log_date
        )

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        return crud_user_daily_log.add_chatbot_message(
            db=db, log_id=daily_log.id, message=message
        )

    def get_chatbot_conversation(
        self, db: Session, *, user_id: UUID, log_date: date
    ) -> List[Dict[str, Any]]:
        """Get chatbot conversation for a specific date."""
        chatbot = crud_user_daily_log.get_chatbot_log_by_user_and_date(
            db=db, user_id=user_id, day=log_date
        )
        return chatbot.conversation if chatbot and chatbot.conversation else []

    def delete_chatbot_message(
        self, db: Session, *, user_id: UUID, log_date: date, message_index: int
    ) -> bool:
        """Delete a specific message from chatbot conversation."""
        daily_log = self.get_or_create_daily_log(
            db=db, user_id=user_id, log_date=log_date
        )
        return crud_user_daily_log.delete_chatbot_message(
            db=db, log_id=daily_log.id, message_index=message_index
        )

    def clear_chatbot_conversation(
        self, db: Session, *, user_id: UUID, log_date: date
    ) -> bool:
        """Clear all messages from chatbot conversation."""
        daily_log = self.get_or_create_daily_log(
            db=db, user_id=user_id, log_date=log_date
        )
        return crud_user_daily_log.clear_chatbot_conversation(
            db=db, log_id=daily_log.id
        )

    # ====================================================
    # ACTIVITY OPERATIONS
    # ====================================================

    def initialize_daily_activities(
        self, db: Session, *, user_id: UUID, log_date: date
    ) -> models.UserActivityTracker:
        """
        Initialize daily activities from user priorities.
        Copies activities and sets complete=0 for all.
        This is a manual initialization method if needed.
        """
        daily_log = self.get_or_create_daily_log(
            db=db, user_id=user_id, log_date=log_date
        )

        # Check if activities already exist and have data
        existing = crud_user_daily_log.get_activities(db=db, log_id=daily_log.id)
        if existing:
            # Check if activities are already populated
            has_activities = any([
                existing.health_activity,
                existing.work_activity,
                existing.growth_activity,
                existing.relationship_activity
            ])
            if has_activities:
                return existing

        # Get user priorities
        try:
            all_activities = self.get_all_user_activities(db=db, user_id=user_id)
            
            # Populate the tracker
            activities_dict = {
                "health": self._reset_activity_complete_values(
                    all_activities.get("health", [])
                ),
                "work": self._reset_activity_complete_values(
                    all_activities.get("work", [])
                ),
                "growth": self._reset_activity_complete_values(
                    all_activities.get("growth", [])
                ),
                "relationships": self._reset_activity_complete_values(
                    all_activities.get("relationships", [])
                )
            }
            
            # Update the existing tracker
            return crud_user_daily_log.populate_activities_from_priorities(
                db=db,
                log_id=daily_log.id,
                activities_data=activities_dict
            )
            
        except PrioritiesNotFoundError:
            raise ValueError("No user priorities found. Please set priorities first.")

    def get_activities_by_date(
        self, db: Session, *, user_id: UUID, log_date: date
    ) -> Optional[models.UserActivityTracker]:
        """Get all activities for a specific date."""
        return crud_user_daily_log.get_activities_by_user_and_date(
            db=db, user_id=user_id, day=log_date
        )

    def _find_activity_in_tracker(
        self,
        tracker: models.UserActivityTracker,
        activity_name: str,
        category: Optional[str] = None,
    ) -> tuple[Optional[Dict], Optional[str]]:
        """
        Find an activity in the tracker.
        Returns (activity_dict, field_name) or (None, None).
        """
        # Map category to field names
        category_map = {
            "health": ["health_activity", "health_coping"],
            "work": ["work_activity", "productivity_coping"],
            "growth": ["growth_activity", "mindfulness_coping"],
            "relationships": ["relationship_activity", "relationship_coping"],
            "relationship": ["relationship_activity", "relationship_coping"],
        }

        # Determine fields to search
        if category:
            field_names = category_map.get(category, [])
        else:
            field_names = [
                "health_activity",
                "work_activity",
                "growth_activity",
                "relationship_activity",
                "health_coping",
                "productivity_coping",
                "mindfulness_coping",
                "relationship_coping",
            ]

        # Search for activity
        for field_name in field_names:
            activity_list = getattr(tracker, field_name, None)
            if not activity_list:
                continue

            for idx, activity in enumerate(activity_list):
                if activity.get("name") == activity_name:
                    return (activity, field_name)

        return (None, None)

    def update_activity_complete(
        self,
        db: Session,
        *,
        user_id: UUID,
        log_date: date,
        activity_name: str,
        complete_value: float,
        category: Optional[str] = None,
    ) -> models.UserActivityTracker:
        """Update activity complete value."""
        if complete_value < 0:
            raise ValueError("Complete value must be non-negative")

        tracker = self.get_activities_by_date(db=db, user_id=user_id, log_date=log_date)
        
        # Auto-initialize if tracker doesn't exist or is empty
        if not tracker or not self._has_activities(tracker):
            tracker = self.initialize_daily_activities(
                db=db, user_id=user_id, log_date=log_date
            )

        activity, field_name = self._find_activity_in_tracker(
            tracker, activity_name, category
        )

        if not activity:
            raise ValueError(f"Activity '{activity_name}' not found")

        # Update complete value
        activity["configuration"]["complete"] = complete_value

        # Force SQLAlchemy to detect the change
        flag_modified(tracker, field_name)

        db.commit()
        db.refresh(tracker)
        return tracker

    def increment_activity_complete(
        self,
        db: Session,
        *,
        user_id: UUID,
        log_date: date,
        activity_name: str,
        increment: float,
        category: Optional[str] = None,
    ) -> models.UserActivityTracker:
        """Increment activity complete value."""
        tracker = self.get_activities_by_date(db=db, user_id=user_id, log_date=log_date)
        
        # Auto-initialize if tracker doesn't exist or is empty
        if not tracker or not self._has_activities(tracker):
            tracker = self.initialize_daily_activities(
                db=db, user_id=user_id, log_date=log_date
            )

        activity, field_name = self._find_activity_in_tracker(
            tracker, activity_name, category
        )

        if not activity:
            raise ValueError(f"Activity '{activity_name}' not found")

        # Increment value
        current = activity["configuration"].get("complete", 0)
        new_value = max(0, current + increment)  # Don't go below 0
        activity["configuration"]["complete"] = new_value

        flag_modified(tracker, field_name)

        db.commit()
        db.refresh(tracker)
        return tracker

    def reset_activity(
        self,
        db: Session,
        *,
        user_id: UUID,
        log_date: date,
        activity_name: str,
        category: Optional[str] = None,
    ) -> models.UserActivityTracker:
        """Reset specific activity to 0."""
        return self.update_activity_complete(
            db=db,
            user_id=user_id,
            log_date=log_date,
            activity_name=activity_name,
            complete_value=0,
            category=category,
        )

    def reset_category_activities(
        self, db: Session, *, user_id: UUID, log_date: date, category: str
    ) -> models.UserActivityTracker:
        """Reset all activities in a category to 0."""
        tracker = self.get_activities_by_date(db=db, user_id=user_id, log_date=log_date)
        
        # Auto-initialize if tracker doesn't exist or is empty
        if not tracker or not self._has_activities(tracker):
            tracker = self.initialize_daily_activities(
                db=db, user_id=user_id, log_date=log_date
            )

        category_map = {
            "health": ["health_activity", "health_coping"],
            "work": ["work_activity", "productivity_coping"],
            "growth": ["growth_activity", "mindfulness_coping"],
            "relationships": ["relationship_activity", "relationship_coping"],
            "relationship": ["relationship_activity", "relationship_coping"],
        }

        field_names = category_map.get(category, [])
        if not field_names:
            raise ValueError(f"Invalid category: {category}")

        for field_name in field_names:
            activity_list = getattr(tracker, field_name, None)
            if activity_list:
                for activity in activity_list:
                    activity["configuration"]["complete"] = 0
                flag_modified(tracker, field_name)

        db.commit()
        db.refresh(tracker)
        return tracker

    def reset_all_activities(
        self, db: Session, *, user_id: UUID, log_date: date
    ) -> models.UserActivityTracker:
        """Reset all activities to 0."""
        tracker = self.get_activities_by_date(db=db, user_id=user_id, log_date=log_date)
        
        # Auto-initialize if tracker doesn't exist or is empty
        if not tracker or not self._has_activities(tracker):
            tracker = self.initialize_daily_activities(
                db=db, user_id=user_id, log_date=log_date
            )

        field_names = [
            "health_activity",
            "work_activity",
            "growth_activity",
            "relationship_activity",
            "health_coping",
            "productivity_coping",
            "mindfulness_coping",
            "relationship_coping",
        ]

        for field_name in field_names:
            activity_list = getattr(tracker, field_name, None)
            if activity_list:
                for activity in activity_list:
                    activity["configuration"]["complete"] = 0
                flag_modified(tracker, field_name)

        db.commit()
        db.refresh(tracker)
        return tracker

    def get_activity_by_name(
        self,
        db: Session,
        *,
        user_id: UUID,
        log_date: date,
        activity_name: str,
        category: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get specific activity by name."""
        tracker = self.get_activities_by_date(db=db, user_id=user_id, log_date=log_date)
        if not tracker:
            return None

        activity, _ = self._find_activity_in_tracker(tracker, activity_name, category)
        return activity

    def get_completion_percentage(
        self,
        db: Session,
        *,
        user_id: UUID,
        log_date: date,
        activity_name: str,
        category: Optional[str] = None,
    ) -> Optional[float]:
        """Calculate completion percentage for an activity."""
        activity = self.get_activity_by_name(
            db=db,
            user_id=user_id,
            log_date=log_date,
            activity_name=activity_name,
            category=category,
        )

        if not activity:
            return None

        config = activity.get("configuration", {})
        complete = config.get("complete", 0)
        quota = config.get("quota", {}).get("value", 0)

        if quota == 0:
            return 0.0

        percentage = (complete / quota) * 100
        return min(round(percentage, 2), 100.0)

    def get_activity_progress_summary(
        self, db: Session, *, user_id: UUID, log_date: date
    ) -> Dict[str, Any]:
        """Get summary of activity progress for the day."""
        tracker = self.get_activities_by_date(db=db, user_id=user_id, log_date=log_date)

        if not tracker:
            return {
                "total": 0,
                "completed": 0,
                "in_progress": 0,
                "not_started": 0,
                "completion_rate": 0.0,
            }

        total = 0
        completed = 0
        in_progress = 0
        not_started = 0

        field_names = [
            "health_activity",
            "work_activity",
            "growth_activity",
            "relationship_activity",
        ]

        for field_name in field_names:
            activity_list = getattr(tracker, field_name, None)
            if not activity_list:
                continue

            for activity in activity_list:
                total += 1
                config = activity.get("configuration", {})
                complete = config.get("complete", 0)
                quota = config.get("quota", {}).get("value", 0)

                if complete == 0:
                    not_started += 1
                elif quota > 0 and complete >= quota:
                    completed += 1
                else:
                    in_progress += 1

        completion_rate = (completed / total * 100) if total > 0 else 0.0

        return {
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "not_started": not_started,
            "completion_rate": round(completion_rate, 2),
        }

    def get_activity_streak(
        self,
        db: Session,
        *,
        user_id: UUID,
        activity_name: str,
        category: Optional[str] = None,
        days_to_check: int = 30,
    ) -> Dict[str, Any]:
        """Calculate streak for a specific activity."""
        today = date.today()
        current_streak = 0
        longest_streak = 0
        temp_streak = 0

        for i in range(days_to_check):
            check_date = today - timedelta(days=i)
            activity = self.get_activity_by_name(
                db=db,
                user_id=user_id,
                log_date=check_date,
                activity_name=activity_name,
                category=category,
            )

            if activity:
                config = activity.get("configuration", {})
                complete = config.get("complete", 0)
                quota = config.get("quota", {}).get("value", 0)

                # Activity counts if it meets quota or has progress
                met_goal = (quota > 0 and complete >= quota) or (quota == 0 and complete > 0)

                if met_goal:
                    temp_streak += 1
                    if i == current_streak:  # Consecutive from today
                        current_streak += 1
                    longest_streak = max(longest_streak, temp_streak)
                else:
                    temp_streak = 0
            else:
                temp_streak = 0

        return {
            "activity_name": activity_name,
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "days_checked": days_to_check,
        }

    def generate_daily_summary(
        self, db: Session, *, user_id: UUID, log_date: date
    ) -> str:
        """Generate AI-ready summary of the day."""
        data = self.get_daily_log_with_details(
            db=db, user_id=user_id, log_date=log_date
        )

        if not data:
            return "No data available for this date."

        summary_parts = []

        # Checkin summary
        latest_checkin = self.get_latest_checkin_values(
            db=db, user_id=user_id, log_date=log_date
        )
        if any(latest_checkin.values()):
            summary_parts.append(
                f"Latest check-in: Mood: {latest_checkin.get('mood')}, "
                f"Stress: {latest_checkin.get('stress_level')}, "
                f"Energy: {latest_checkin.get('energy_level')}"
            )

        # Activity summary
        progress = self.get_activity_progress_summary(
            db=db, user_id=user_id, log_date=log_date
        )
        summary_parts.append(
            f"Activities: {progress['completed']}/{progress['total']} completed "
            f"({progress['completion_rate']}%)"
        )

        # Journal entries
        journal_count = len(data["journal"]["entries"])
        if journal_count > 0:
            summary_parts.append(f"{journal_count} journal entries")

        # Chat interactions
        chat_count = len(data["chatbot"]["conversation"])
        if chat_count > 0:
            summary_parts.append(f"{chat_count} chat messages")

        return " | ".join(summary_parts)

    # ====================================================
    # BULK OPERATIONS
    # ====================================================

    def bulk_update_activities(
        self,
        db: Session,
        *,
        user_id: UUID,
        log_date: date,
        updates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Bulk update multiple activities at once.
        
        Args:
            updates: List of dicts with keys: name, complete, category (optional)
        
        Returns:
            Dict with success_count, error_count, and errors list
        """
        success_count = 0
        error_count = 0
        errors = []

        for update in updates:
            try:
                activity_name = update.get("name")
                complete_value = update.get("complete")
                category = update.get("category")

                if not activity_name or complete_value is None:
                    errors.append(f"Invalid update data: {update}")
                    error_count += 1
                    continue

                self.update_activity_complete(
                    db=db,
                    user_id=user_id,
                    log_date=log_date,
                    activity_name=activity_name,
                    complete_value=complete_value,
                    category=category
                )
                success_count += 1

            except Exception as e:
                errors.append(f"Failed to update '{update.get('name')}': {str(e)}")
                error_count += 1

        return {
            "success_count": success_count,
            "error_count": error_count,
            "errors": errors,
            "message": f"Bulk update completed: {success_count} succeeded, {error_count} failed"
        }

    def get_category_progress(
        self,
        db: Session,
        *,
        user_id: UUID,
        log_date: date,
        category: str
    ) -> Dict[str, Any]:
        """Get progress summary for a specific category."""
        tracker = self.get_activities_by_date(db=db, user_id=user_id, log_date=log_date)

        if not tracker:
            return {
                "category": category,
                "activities": [],
                "total_activities": 0,
                "completed_activities": 0,
                "completion_rate": 0.0
            }

        category_map = {
            "health": ["health_activity", "health_coping"],
            "work": ["work_activity", "productivity_coping"],
            "growth": ["growth_activity", "mindfulness_coping"],
            "relationships": ["relationship_activity", "relationship_coping"],
            "relationship": ["relationship_activity", "relationship_coping"],
        }

        field_names = category_map.get(category, [])
        activities_list = []
        total = 0
        completed = 0

        for field_name in field_names:
            activity_list = getattr(tracker, field_name, None)
            if not activity_list:
                continue

            for activity in activity_list:
                config = activity.get("configuration", {})
                complete = config.get("complete", 0)
                quota = config.get("quota", {}).get("value", 0)
                
                percentage = (complete / quota * 100) if quota > 0 else 0
                
                activities_list.append({
                    "name": activity.get("name"),
                    "complete": complete,
                    "quota": quota,
                    "percentage": round(percentage, 2)
                })
                
                total += 1
                if quota > 0 and complete >= quota:
                    completed += 1

        completion_rate = (completed / total * 100) if total > 0 else 0.0

        return {
            "category": category,
            "activities": activities_list,
            "total_activities": total,
            "completed_activities": completed,
            "completion_rate": round(completion_rate, 2)
        }

    def validate_activity(
        self,
        db: Session,
        *,
        user_id: UUID,
        log_date: date,
        activity_name: str,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """Validate if an activity exists and can be tracked."""
        activity = self.get_activity_by_name(
            db=db,
            user_id=user_id,
            log_date=log_date,
            activity_name=activity_name,
            category=category
        )

        if not activity:
            return {
                "is_valid": False,
                "activity_name": activity_name,
                "exists": False,
                "has_quota": False,
                "can_track_progress": False,
                "messages": [f"Activity '{activity_name}' not found"]
            }

        config = activity.get("configuration", {})
        quota = config.get("quota", {})
        has_quota = quota.get("value", 0) > 0

        return {
            "is_valid": True,
            "activity_name": activity_name,
            "exists": True,
            "has_quota": has_quota,
            "can_track_progress": True,
            "messages": []
        }


# Create singleton instance
user_daily_log_service = UserDailyLogService()