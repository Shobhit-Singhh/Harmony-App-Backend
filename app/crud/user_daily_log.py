from sqlalchemy.orm import Session
from uuid import UUID
from datetime import date, datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm.attributes import flag_modified
from app import models
from app.schemas import user_daily_logs as schemas


class CRUDUserDailyLog:
    # ====================================================
    # MAIN DAILY LOG
    # ====================================================

    def create(self, db: Session, *, obj_in: schemas.UserDailyLogBase):
        """Create a new daily log with empty child records"""
        daily_log = models.UserDailyLog(
            user_id=obj_in.user_id,
            date=obj_in.date,
            current_status_summary=obj_in.current_status_summary,
            frequency=obj_in.frequency,
            active_hours=obj_in.active_hours,
        )
        db.add(daily_log)
        db.flush()

        # Auto-create empty children
        empty_json = {}
        db.add(
            models.UserCheckin(
                id=daily_log.id,
                mood=empty_json,
                stress_level=empty_json,
                energy_level=empty_json,
                sleep=empty_json,
            )
        )
        db.add(models.UserChatbotLog(id=daily_log.id, conversation=[], analysis={}))
        db.add(models.UserJournal(id=daily_log.id, journal={}, analysis={}))
        db.add(
            models.UserActivityTracker(
                id=daily_log.id,
                health_activity=[],
                work_activity=[],
                growth_activity=[],
                relationship_activity=[],
                health_coping=[],
                productivity_coping=[],
                mindfulness_coping=[],
                relationship_coping=[],
            )
        )

        db.commit()
        db.refresh(daily_log)
        return daily_log

    def create_with_activities(
        self, db: Session, *, obj_in: schemas.UserDailyLogCreate
    ) -> models.UserDailyLog:
        """Create a new daily log with populated activities from priorities."""
        daily_log = models.UserDailyLog(
            user_id=obj_in.user_id,
            date=obj_in.date,
            current_status_summary=obj_in.current_status_summary,
            frequency=obj_in.frequency or {},
            active_hours=obj_in.active_hours or {},
        )
        db.add(daily_log)
        db.flush()

        # Create empty children first
        empty_json = {}
        
        # Checkin
        if obj_in.checkin:
            db.add(
                models.UserCheckin(
                    id=daily_log.id,
                    mood=obj_in.checkin.mood,
                    stress_level=obj_in.checkin.stress_level,
                    energy_level=obj_in.checkin.energy_level,
                    sleep=obj_in.checkin.sleep,
                )
            )
        else:
            db.add(
                models.UserCheckin(
                    id=daily_log.id,
                    mood=empty_json,
                    stress_level=empty_json,
                    energy_level=empty_json,
                    sleep=empty_json,
                )
            )

        # Chatbot Log
        if obj_in.chatbot_log:
            db.add(
                models.UserChatbotLog(
                    id=daily_log.id,
                    conversation=obj_in.chatbot_log.conversation,
                    analysis=obj_in.chatbot_log.analysis,
                )
            )
        else:
            db.add(
                models.UserChatbotLog(
                    id=daily_log.id, 
                    conversation=[], 
                    analysis={}
                )
            )

        # Journal
        if obj_in.journal:
            db.add(
                models.UserJournal(
                    id=daily_log.id,
                    journal=obj_in.journal.journal,
                    analysis=obj_in.journal.analysis,
                )
            )
        else:
            db.add(
                models.UserJournal(
                    id=daily_log.id, 
                    journal={}, 
                    analysis={}
                )
            )

        # Activities - POPULATE FROM PRIORITIES
        if obj_in.activities:
            # Convert to plain lists if Pydantic models
            def to_list(items):
                if not items:
                    return []
                return [item.dict() if hasattr(item, 'dict') else item for item in items]
            
            db.add(
                models.UserActivityTracker(
                    id=daily_log.id,
                    health_activity=to_list(obj_in.activities.health_activity),
                    work_activity=to_list(obj_in.activities.work_activity),
                    growth_activity=to_list(obj_in.activities.growth_activity),
                    relationship_activity=to_list(obj_in.activities.relationship_activity),
                    health_coping=to_list(obj_in.activities.health_coping),
                    productivity_coping=to_list(obj_in.activities.productivity_coping),
                    mindfulness_coping=to_list(obj_in.activities.mindfulness_coping),
                    relationship_coping=to_list(obj_in.activities.relationship_coping),
                )
            )
        else:
            db.add(
                models.UserActivityTracker(
                    id=daily_log.id,
                    health_activity=[],
                    work_activity=[],
                    growth_activity=[],
                    relationship_activity=[],
                    health_coping=[],
                    productivity_coping=[],
                    mindfulness_coping=[],
                    relationship_coping=[],
                )
            )

        db.commit()
        db.refresh(daily_log)
        return daily_log

    def populate_activities_from_priorities(
        self, 
        db: Session, 
        *, 
        log_id: UUID,
        activities_data: Dict[str, List[Dict[str, Any]]]
    ) -> models.UserActivityTracker:
        """Populate an existing activity tracker with data from priorities."""
        tracker = self.get_activities(db=db, log_id=log_id)
        if not tracker:
            raise ValueError("Activity tracker not found")
        
        # Update each field
        tracker.health_activity = activities_data.get("health", [])
        tracker.work_activity = activities_data.get("work", [])
        tracker.growth_activity = activities_data.get("growth", [])
        tracker.relationship_activity = activities_data.get("relationships", [])
        
        # Mark all fields as modified
        flag_modified(tracker, "health_activity")
        flag_modified(tracker, "work_activity")
        flag_modified(tracker, "growth_activity")
        flag_modified(tracker, "relationship_activity")
        
        tracker.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(tracker)
        return tracker

    def get_by_id(self, db: Session, *, log_id: UUID) -> Optional[models.UserDailyLog]:
        """Get daily log by ID"""
        return (
            db.query(models.UserDailyLog)
            .filter(models.UserDailyLog.id == log_id)
            .first()
        )

    def get_by_user_and_date(
        self, db: Session, *, user_id: UUID, day: date
    ) -> Optional[models.UserDailyLog]:
        """Get daily log for a specific user and date"""
        return (
            db.query(models.UserDailyLog)
            .filter(models.UserDailyLog.user_id == user_id)
            .filter(models.UserDailyLog.date == day)
            .first()
        )

    def get_all_by_user(
        self, db: Session, *, user_id: UUID, skip: int = 0, limit: int = 50
    ) -> list[models.UserDailyLog]:
        """Get all daily logs for a user with pagination"""
        return (
            db.query(models.UserDailyLog)
            .filter(models.UserDailyLog.user_id == user_id)
            .order_by(models.UserDailyLog.date.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_date_range(
        self, db: Session, *, user_id: UUID, start_date: date, end_date: date
    ) -> list[models.UserDailyLog]:
        """Get daily logs within a date range"""
        return (
            db.query(models.UserDailyLog)
            .filter(models.UserDailyLog.user_id == user_id)
            .filter(models.UserDailyLog.date >= start_date)
            .filter(models.UserDailyLog.date <= end_date)
            .order_by(models.UserDailyLog.date.asc())
            .all()
        )

    def update(
        self,
        db: Session,
        *,
        db_obj: models.UserDailyLog,
        obj_in: schemas.UserDailyLogUpdate,
    ) -> models.UserDailyLog:
        """Update main daily log fields only"""
        for field, value in obj_in.dict(exclude_unset=True).items():
            if field not in ["checkin", "chatbot_log", "journal", "activities"]:
                setattr(db_obj, field, value)

        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete_by_id(self, db: Session, *, log_id: UUID) -> bool:
        """Delete daily log by ID"""
        db_obj = self.get_by_id(db, log_id=log_id)
        if db_obj:
            db.delete(db_obj)
            db.commit()
            return True
        return False

    def delete_by_date(self, db: Session, *, user_id: UUID, day: date) -> bool:
        """Delete daily log for a specific user and date"""
        db_obj = self.get_by_user_and_date(db, user_id=user_id, day=day)
        if db_obj:
            db.delete(db_obj)
            db.commit()
            return True
        return False

    # ====================================================
    # USER CHECKIN
    # ====================================================

    def get_checkin(self, db: Session, *, log_id: UUID) -> Optional[models.UserCheckin]:
        """Get checkin data for a daily log"""
        return (
            db.query(models.UserCheckin).filter(models.UserCheckin.id == log_id).first()
        )

    def get_checkin_by_user_and_date(
        self, db: Session, *, user_id: UUID, day: date
    ) -> Optional[models.UserCheckin]:
        """Get checkin data for a specific user and date"""
        daily_log = self.get_by_user_and_date(db, user_id=user_id, day=day)
        if daily_log:
            return self.get_checkin(db, log_id=daily_log.id)
        return None

    def update_checkin(
        self, db: Session, *, log_id: UUID, obj_in: schemas.UserCheckinUpdate
    ) -> Optional[models.UserCheckin]:
        """Merge new values with existing values for specific fields."""
        checkin = self.get_checkin(db, log_id=log_id)
        if not checkin:
            return None

        for field, new_value in obj_in.dict(exclude_unset=True).items():
            if new_value is not None:
                existing_data = getattr(checkin, field, {}) or {}

                if isinstance(new_value, dict) and isinstance(existing_data, dict):
                    existing_data.update(new_value)
                    setattr(checkin, field, existing_data)
                else:
                    setattr(checkin, field, new_value)

        for field in obj_in.dict(exclude_unset=True).keys():
            flag_modified(checkin, field)

        db.commit()
        db.refresh(checkin)
        return checkin

    def delete_checkin(self, db: Session, *, log_id: UUID) -> bool:
        """Delete checkin data (resets to empty)"""
        checkin = self.get_checkin(db, log_id=log_id)
        if checkin:
            empty_json = {}
            checkin.mood = empty_json
            checkin.stress_level = empty_json
            checkin.energy_level = empty_json
            checkin.sleep = empty_json
            db.commit()
            return True
        return False

    # ====================================================
    # JOURNAL
    # ====================================================
    
    def get_journal(self, db: Session, *, log_id: UUID) -> Optional[models.UserJournal]:
        """Get journal for a daily log."""
        return (
            db.query(models.UserJournal).filter(models.UserJournal.id == log_id).first()
        )

    def get_journal_by_user_and_date(
        self, db: Session, *, user_id: UUID, day: date
    ) -> Optional[models.UserJournal]:
        """Get journal for a specific user and date."""
        daily_log = self.get_by_user_and_date(db, user_id=user_id, day=day)
        return self.get_journal(db, log_id=daily_log.id) if daily_log else None

    def add_journal_entry(
        self,
        db: Session,
        *,
        log_id: UUID,
        timestamp: datetime,
        entry_type: str,
        content: str,
        sentiment: Optional[str] = None,
        topics: Optional[List[str]] = None,
    ) -> models.UserJournal:
        """Add a new journal entry."""
        journal = self.get_journal(db, log_id=log_id)
        if not journal:
            raise ValueError("Journal not found")

        timestamp_str = timestamp.isoformat()
        current_journal = journal.journal or {}

        if timestamp_str in current_journal:
            raise ValueError(f"Entry already exists at {timestamp_str}")

        current_journal[timestamp_str] = [entry_type, content, sentiment, topics or []]
        journal.journal = current_journal
        journal.last_updated_at = datetime.utcnow()

        flag_modified(journal, "journal")
        db.commit()
        db.refresh(journal)
        return journal

    def update_journal_entry(
        self,
        db: Session,
        *,
        log_id: UUID,
        timestamp: datetime,
        entry_type: Optional[str] = None,
        content: Optional[str] = None,
        sentiment: Optional[str] = None,
        topics: Optional[List[str]] = None,
    ) -> models.UserJournal:
        """Update an existing journal entry."""
        journal = self.get_journal(db, log_id=log_id)
        if not journal:
            raise ValueError("Journal not found")

        timestamp_str = timestamp.isoformat()
        current_journal = journal.journal or {}

        if timestamp_str not in current_journal:
            raise ValueError(f"Entry not found at {timestamp_str}")

        existing = current_journal[timestamp_str]

        current_journal[timestamp_str] = [
            entry_type if entry_type is not None else existing[0],
            content if content is not None else existing[1],
            sentiment if sentiment is not None else existing[2],
            topics if topics is not None else existing[3],
        ]

        journal.journal = current_journal
        journal.last_updated_at = datetime.utcnow()

        flag_modified(journal, "journal")
        db.commit()
        db.refresh(journal)
        return journal

    def delete_journal_entry(
        self, db: Session, *, log_id: UUID, timestamp: datetime
    ) -> bool:
        """Delete a journal entry."""
        journal = self.get_journal(db, log_id=log_id)
        if not journal:
            return False

        timestamp_str = timestamp.isoformat()
        current_journal = journal.journal or {}

        if timestamp_str not in current_journal:
            return False

        del current_journal[timestamp_str]
        journal.journal = current_journal
        journal.last_updated_at = datetime.utcnow()

        flag_modified(journal, "journal")
        db.commit()
        return True

    # ====================================================
    # CHATBOT LOG
    # ====================================================

    def get_chatbot_log(
        self, db: Session, *, log_id: UUID
    ) -> Optional[models.UserChatbotLog]:
        """Get chatbot log for a daily log."""
        return (
            db.query(models.UserChatbotLog)
            .filter(models.UserChatbotLog.id == log_id)
            .first()
        )

    def get_chatbot_log_by_user_and_date(
        self, db: Session, *, user_id: UUID, day: date
    ) -> Optional[models.UserChatbotLog]:
        """Get chatbot log for a specific user and date."""
        daily_log = self.get_by_user_and_date(db, user_id=user_id, day=day)
        return self.get_chatbot_log(db, log_id=daily_log.id) if daily_log else None

    def add_chatbot_message(
        self, db: Session, *, log_id: UUID, message: dict
    ) -> models.UserChatbotLog:
        """Add a new message to chatbot conversation."""
        chatbot = self.get_chatbot_log(db, log_id=log_id)
        if not chatbot:
            raise ValueError("Chatbot log not found")

        current_conversation = chatbot.conversation or []
        current_conversation.append(message)

        chatbot.conversation = current_conversation
        chatbot.last_updated_at = datetime.utcnow()

        flag_modified(chatbot, "conversation")
        db.commit()
        db.refresh(chatbot)
        return chatbot

    def delete_chatbot_message(
        self, db: Session, *, log_id: UUID, message_index: int
    ) -> bool:
        """Delete a specific message from chatbot conversation."""
        chatbot = self.get_chatbot_log(db, log_id=log_id)
        if not chatbot or not chatbot.conversation:
            return False

        if message_index < 0 or message_index >= len(chatbot.conversation):
            return False

        current_conversation = chatbot.conversation
        current_conversation.pop(message_index)

        chatbot.conversation = current_conversation
        chatbot.last_updated_at = datetime.utcnow()

        flag_modified(chatbot, "conversation")
        db.commit()
        return True

    def clear_chatbot_conversation(self, db: Session, *, log_id: UUID) -> bool:
        """Clear all messages from chatbot conversation."""
        chatbot = self.get_chatbot_log(db, log_id=log_id)
        if not chatbot:
            return False

        chatbot.conversation = []
        chatbot.analysis = {}
        chatbot.last_updated_at = datetime.utcnow()

        flag_modified(chatbot, "conversation")
        flag_modified(chatbot, "analysis")
        db.commit()
        return True

    # ====================================================
    # ACTIVITY TRACKER
    # ====================================================
    
    def get_activities(self, db: Session, *, log_id: UUID) -> Optional[models.UserActivityTracker]:
        """Get activity tracker for a daily log."""
        return db.query(models.UserActivityTracker).filter(
            models.UserActivityTracker.id == log_id
        ).first()

    def get_activities_by_user_and_date(
        self, db: Session, *, user_id: UUID, day: date
    ) -> Optional[models.UserActivityTracker]:
        """Get activities for a specific user and date."""
        daily_log = self.get_by_user_and_date(db, user_id=user_id, day=day)
        return self.get_activities(db, log_id=daily_log.id) if daily_log else None

    def _get_category_fields(self, category: str = None) -> list:
        """Map category names to actual field names."""
        category_mapping = {
            "health": ["health_activity", "health_coping"],
            "work": ["work_activity", "productivity_coping"],
            "growth": ["growth_activity", "mindfulness_coping"],
            "relationship": ["relationship_activity", "relationship_coping"],
            "relationships": ["relationship_activity", "relationship_coping"],
        }
        
        if category:
            return category_mapping.get(category, [])
        
        all_fields = []
        for fields in category_mapping.values():
            all_fields.extend(fields)
        return list(set(all_fields))

    def update_activity_complete(
        self, 
        db: Session, 
        *, 
        log_id: UUID, 
        activity_name: str, 
        complete_value: int, 
        category: str = None
    ) -> models.UserActivityTracker:
        """Update the complete value of an activity in its configuration."""
        activities = self.get_activities(db, log_id=log_id)
        if not activities:
            raise ValueError("Activity tracker not found")
        
        fields_to_search = self._get_category_fields(category)
        
        for field_name in fields_to_search:
            activity_list = getattr(activities, field_name, None)
            if not activity_list:
                continue
            
            activity_list = list(activity_list)
            
            for activity in activity_list:
                if activity.get("name") == activity_name:
                    if "configuration" not in activity:
                        activity["configuration"] = {}
                    
                    activity["configuration"]["complete"] = complete_value
                    
                    setattr(activities, field_name, activity_list)
                    flag_modified(activities, field_name)
                    activities.updated_at = datetime.utcnow()
                    
                    db.commit()
                    db.refresh(activities)
                    return activities
        
        raise ValueError(f"Activity '{activity_name}' not found in specified category")

    def increment_activity_complete(
        self, 
        db: Session, 
        *, 
        log_id: UUID, 
        activity_name: str, 
        increment: int, 
        category: str = None
    ) -> models.UserActivityTracker:
        """Increment the complete value of an activity."""
        activities = self.get_activities(db, log_id=log_id)
        if not activities:
            raise ValueError("Activity tracker not found")
        
        fields_to_search = self._get_category_fields(category)
        
        for field_name in fields_to_search:
            activity_list = getattr(activities, field_name, None)
            if not activity_list:
                continue
            
            activity_list = list(activity_list)
            
            for activity in activity_list:
                if activity.get("name") == activity_name:
                    config = activity.get("configuration", {})
                    current_complete = config.get("complete", 0)
                    
                    config["complete"] = current_complete + increment
                    activity["configuration"] = config
                    
                    setattr(activities, field_name, activity_list)
                    flag_modified(activities, field_name)
                    activities.updated_at = datetime.utcnow()
                    
                    db.commit()
                    db.refresh(activities)
                    return activities
        
        raise ValueError(f"Activity '{activity_name}' not found in specified category")

    def reset_activity_complete(
        self, 
        db: Session, 
        *, 
        log_id: UUID, 
        activity_name: str, 
        category: str = None
    ) -> models.UserActivityTracker:
        """Reset the complete value of an activity to 0."""
        return self.update_activity_complete(
            db=db, 
            log_id=log_id, 
            activity_name=activity_name, 
            complete_value=0, 
            category=category
        )

    def reset_category_activities(
        self, 
        db: Session, 
        *, 
        log_id: UUID, 
        category: str
    ) -> models.UserActivityTracker:
        """Reset all activities in a category to complete=0."""
        activities = self.get_activities(db, log_id=log_id)
        if not activities:
            raise ValueError("Activity tracker not found")
        
        field_names = self._get_category_fields(category)
        
        for field_name in field_names:
            activity_list = getattr(activities, field_name, None)
            if not activity_list:
                continue
            
            activity_list = list(activity_list)
            
            for activity in activity_list:
                if "configuration" not in activity:
                    activity["configuration"] = {}
                activity["configuration"]["complete"] = 0
            
            setattr(activities, field_name, activity_list)
            flag_modified(activities, field_name)
        
        activities.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(activities)
        return activities

    def reset_all_activities(
        self, 
        db: Session, 
        *, 
        log_id: UUID
    ) -> models.UserActivityTracker:
        """Reset all activities to complete=0."""
        categories = ["health", "work", "growth", "relationship"]
        
        for category in categories:
            try:
                self.reset_category_activities(db=db, log_id=log_id, category=category)
            except Exception:
                continue
        
        return self.get_activities(db, log_id=log_id)

    def get_activity_progress_summary(
        self, 
        db: Session, 
        *, 
        user_id: UUID, 
        log_date: date
    ) -> Dict[str, Any]:
        """Get summary of activity progress for the day."""
        activities = self.get_activities_by_user_and_date(
            db=db, user_id=user_id, day=log_date
        )
        
        if not activities:
            return {
                "total": 0, 
                "completed": 0, 
                "in_progress": 0, 
                "not_started": 0, 
                "completion_rate": 0
            }
        
        total = completed = in_progress = not_started = 0
        
        categories = [
            activities.health_activity,
            activities.work_activity,
            activities.growth_activity,
            activities.relationship_activity,
        ]
        
        for category in categories:
            if not category:
                continue
            
            for activity in category:
                total += 1
                
                config = activity.get("configuration", {})
                complete_value = config.get("complete", 0)
                quota_value = config.get("quota", {}).get("value", 0)
                
                if complete_value == 0:
                    not_started += 1
                elif quota_value > 0 and complete_value >= quota_value:
                    completed += 1
                else:
                    in_progress += 1
        
        return {
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "not_started": not_started,
            "completion_rate": round((completed / total * 100), 2) if total > 0 else 0,
        }

    def get_activity_streak(
        self, 
        db: Session, 
        *, 
        user_id: UUID, 
        activity_name: str, 
        category: Optional[str] = None,
        days_to_check: int = 30
    ) -> Dict[str, Any]:
        """Calculate streak for a specific activity."""
        from datetime import timedelta
        
        end_date = date.today()
        start_date = end_date - timedelta(days=days_to_check)
        
        logs = self.get_by_date_range(
            db=db, user_id=user_id, start_date=start_date, end_date=end_date
        )
        
        current_streak = longest_streak = temp_streak = 0
        
        for log in reversed(logs):
            activities = self.get_activities(db=db, log_id=log.id)
            if not activities:
                break
            
            activity_completed = False
            
            if category:
                field_names = self._get_category_fields(category)
                categories_to_check = [getattr(activities, fn, None) for fn in field_names]
            else:
                categories_to_check = [
                    activities.health_activity, 
                    activities.work_activity,
                    activities.growth_activity, 
                    activities.relationship_activity
                ]
            
            for cat in categories_to_check:
                if not cat:
                    continue
                
                for activity in cat:
                    if activity.get("name") == activity_name:
                        config = activity.get("configuration", {})
                        complete_value = config.get("complete", 0)
                        quota_value = config.get("quota", {}).get("value", 0)
                        
                        if quota_value > 0 and complete_value >= quota_value:
                            activity_completed = True
                            break
                        elif quota_value == 0 and complete_value > 0:
                            activity_completed = True
                            break
                
                if activity_completed:
                    break
            
            if activity_completed:
                temp_streak += 1
                longest_streak = max(longest_streak, temp_streak)
            else:
                if current_streak == 0:
                    current_streak = temp_streak
                temp_streak = 0
        
        if current_streak == 0:
            current_streak = temp_streak
        
        return {
            "activity_name": activity_name,
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "days_checked": days_to_check,
        }


# Instantiate a reusable object
crud_user_daily_log = CRUDUserDailyLog()