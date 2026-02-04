"""
Time Aware Context Generator
Generates natural language context for LLM awareness of:
- Current date and day of week
- Time of day (Morning, Afternoon, Evening, Night)
- Holidays and special dates
- Month phase (beginning, middle, end)
- Time gap since last message
"""

from datetime import datetime
from debug_config import DebugConfig


class TimeAwareContext:
    """Generate time-aware context for LLM conversations"""
    
    @staticmethod
    def get_context(message_history):
        """
        Generate comprehensive time-aware context for LLM.
        IMPORTANT: Generates FRESH context every time - no caching!
        
        Args:
            message_history: List of message dicts with 'role', 'content', 'timestamp'
        
        Returns:
            str: Context string like "It's 14:35 (Afternoon). It's Monday."
            Only includes TIME, not date - avoids stale cached values!
        """
        try:
            context_parts = []
            
            # Always use CURRENT time (not from old messages)
            current_ts = datetime.now()
            current_hour = current_ts.hour
            current_minute = current_ts.minute
            current_day = current_ts.day
            current_month = current_ts.month
            
            if DebugConfig.connection_requests:
                print(f"[DEBUG-TIME] TimeAwareContext: Current time = {current_ts}")
            
            # Get day of week (0=Monday, 6=Sunday)
            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            day_of_week = day_names[current_ts.weekday()]
            
            # Get month name
            month_names = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
            month_name = month_names[current_month - 1]
            
            # Determine time of day
            if 5 <= current_hour < 12:
                time_of_day = "Morning"
            elif 12 <= current_hour < 17:
                time_of_day = "Afternoon"
            elif 17 <= current_hour < 21:
                time_of_day = "Evening"
            else:
                time_of_day = "Night"
            
            # Format time naturally (rounded to nearest 5 minutes)
            rounded_minute = (current_minute // 5) * 5
            if rounded_minute == 0:
                natural_time = f"{current_hour:02d}:{rounded_minute:02d}"
            else:
                natural_time = f"{current_hour:02d}:{rounded_minute:02d}"
            
            # Build context string with FULL date info: time, date, month, year, day of week
            context_parts.append(f"{natural_time} on {day_of_week}, {month_name} {current_day}, {current_ts.year}")
            context_parts.append(f"It's {time_of_day.lower()}")
            
            # Add month phase context
            if current_day <= 10:
                month_phase = "beginning of the month"
            elif current_day >= 20:
                month_phase = "end of the month"
            else:
                month_phase = "middle of the month"
            
            context_parts.append(f"This is the {month_phase}")
            
            # Add time gap from last message if available
            # (Disabled - causes issues with cached system prompts in multi-turn conversations)
            # Just return the basic time context
            
            return ". ".join(context_parts) + "."
        except Exception as e:
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] Error generating time context: {e}")
            return ""
    
    @staticmethod
    def _get_holiday_context(month, day):
        """
        Detect holidays and special dates for LLM to naturally reference.
        
        Args:
            month: Month (1-12)
            day: Day of month (1-31)
        
        Returns:
            str: Holiday context string or empty string
        """
        holidays = {
            (1, 1): "Happy New Year!",
            (2, 14): "It's Valentine's Day",
            (3, 17): "It's St. Patrick's Day",
            (4, 22): "It's Earth Day",
            (7, 4): "It's Independence Day (USA)",
            (10, 31): "It's Halloween",
            (11, 11): "It's Veterans Day",
            (12, 25): "Merry Christmas!",
            (12, 31): "It's New Year's Eve",
        }
        
        # Check for exact match
        if (month, day) in holidays:
            return holidays[(month, day)]
        
        # Check for Thanksgiving (4th Thursday of November)
        if month == 11:
            # Calculate 4th Thursday
            first_day = datetime(datetime.now().year, 11, 1)
            from datetime import timedelta
            first_thursday = first_day + timedelta(days=(3 - first_day.weekday()))
            fourth_thursday = first_thursday + timedelta(weeks=3)
            if day == fourth_thursday.day:
                return "It's Thanksgiving"
        
        # Check for Black Friday (day after Thanksgiving in USA)
        if month == 11:
            first_day = datetime(datetime.now().year, 11, 1)
            from datetime import timedelta
            first_thursday = first_day + timedelta(days=(3 - first_day.weekday()))
            fourth_thursday = first_thursday + timedelta(weeks=3)
            black_friday = fourth_thursday + timedelta(days=1)
            if day == black_friday.day:
                return "It's Black Friday"
        
        # Check for Easter (approximate - varies each year)
        # For simplicity, checking late March to mid-April range
        if month == 4 and 1 <= day <= 25:
            return "It's around Easter time"
        
        # Check for beginning/middle/end of month special feelings
        if day == 1:
            return "It's the first day of the month - a fresh start!"
        elif day == 15:
            return "It's the middle of the month"
        
        return ""
