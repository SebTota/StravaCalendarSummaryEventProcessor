from abc import ABC, abstractmethod
from strava_calendar_summary_data_access_layer import User, EndOfWeekType, WeeklySummaryCalendarEventsController, \
    CalendarSummaryEvent, UserController
from strava_calendar_summary_utils import StravaUtil, GoogleCalendarUtil, template_builder

from datetime import datetime, timezone, timedelta
from datetime import date as Date
from dateutil import tz
from stravalib.model import Activity
from typing import Union


def next_specified_day(date: datetime, day: EndOfWeekType) -> datetime:
    """
    Get the date of when the next specify weekday will occur
    :param date: the start date
    :param day: the weekday you are looking for
    :return: the datetime object of the next specified weekday
    """
    days = (day.get_weekday_num_val() - date.weekday() + 7) % 7
    return date + timedelta(days=days)


def get_day_start_and_end_datetime(date: datetime) -> [datetime, datetime]:
    """
    Get the start and end datetime of a specified date in UTC timezone
    :param date: the local date
    :return: [start_datetime_utc: datetime, end_datetime_utc: datetime]
    """
    local_start_datetime: datetime = date

    # Find beginning and end of local date
    local_start_datetime = local_start_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
    local_end_datetime = local_start_datetime.replace(hour=23, minute=59, second=59, microsecond=999999)

    # Find beginning and end of date in UTC
    activity_day_start_time = datetime.fromtimestamp(local_start_datetime.timestamp(), tz=timezone.utc)
    activity_day_end_time = datetime.fromtimestamp(local_start_datetime.timestamp(), tz=timezone.utc)

    return [activity_day_start_time, activity_day_end_time]


def get_week_start_and_end_datetime(date: datetime, last_day_of_week: EndOfWeekType) -> [datetime, datetime]:
    """
    Get the start and end UTC datetime of the week based on a start date and the last weekday of a week
    :param date: the start date - this is NOT when the week will start. it's just a specified day WITHIN the week
    :param last_day_of_week: the last weekday of the week
    :return: [start_datetime_utc: datetime, end_datetime_utc: datetime]
    """
    start_day_datetime_utc, end_day_datetime_utc = get_day_start_and_end_datetime(date)
    start_week_datetime_utc = next_specified_day(start_day_datetime_utc, last_day_of_week) - timedelta(days=7)
    end_week_datetime_utc = next_specified_day(end_day_datetime_utc, last_day_of_week)

    return [start_week_datetime_utc, end_week_datetime_utc]


class SummaryHandler:
    def __init__(self, user: User, user_local_timezone: str):
        self.user: User = user
        self.user_local_timezone: str = user_local_timezone

        self.user_controller: UserController = UserController()
        self.strava_util: StravaUtil = StravaUtil(self.user.strava_credentials, self.user)
        self.weekly_summary_events_controller: WeeklySummaryCalendarEventsController = \
            WeeklySummaryCalendarEventsController(self.user.user_id)
        self.calendar_util: GoogleCalendarUtil = GoogleCalendarUtil(user.calendar_credentials, user=user, calendar_id=user.calendar_id)

    def update_summaries(self, date: datetime):
        """
        Update the daily and/or weekly calendar summaries
        :param date: specific date if daily or any day within the week if weekly
        :return: None
        """

        daily_summary: bool = self.user.calendar_preferences.daily_run_summary_enabled
        weekly_summary: bool = self.user.calendar_preferences.weekly_run_summary_enabled
        if not daily_summary and not weekly_summary:
            return

        activities: [Activity]
        day_start_utc, day_end_utc = get_day_start_and_end_datetime(date)
        week_start_utc, week_end_utc = get_week_start_and_end_datetime(date, self.user.calendar_preferences.end_of_week)

        if weekly_summary:
            activities = self.get_activities(week_start_utc, week_end_utc)
        else:
            activities = self.get_activities(day_start_utc, day_end_utc)

        if weekly_summary:
            self.update_weekly_summary(activities, week_start_utc, week_end_utc)
        # if daily_summary:
        #     self.update_daily_summary(self.get_activities_between_date(activities, day_start_utc, day_end_utc))

    def update_weekly_summary(self, activities: [Activity], start: datetime, end: datetime):
        event_id: Union[None, str] = self.get_weekly_summary_event_id_for_date(end.date())

        title: str = template_builder.fill_summary_template(
            self.user.calendar_preferences.weekly_run_title_template, activities)
        description: str = template_builder.fill_summary_template(
            self.user.calendar_preferences.weekly_run_description_template, activities)
        calendar_event_date: Date = self.get_date_in_local_timezone(end).date()

        if event_id is None:
            # Create a new weekly summary calendar event
            event_id = self.add_summary_event_to_calendar(title, description, self.user_local_timezone, calendar_event_date)
        else:
            # Update the existing weekly summary calendar event
            self.update_summary_event_to_calendar(event_id, title, description, self.user_local_timezone, calendar_event_date)

        self.save_weekly_summary_event_id_for_date(event_id, start, end)

    def get_weekly_summary_event_id_for_date(self, date: Date) -> Union[None, str]:
        """
        Get the calendar event id for a weekly summary calendar event
        :param date: the date indicating the end of the week
        :return: None if there is no event id or a string of the event id if present
        """

        if self.user.weekly_summary_calendar_event is not None and \
                date == self.user.weekly_summary_calendar_event.end_datetime.date():
            return self.user.weekly_summary_calendar_event.calendar_event_id

        entry: CalendarSummaryEvent = self.weekly_summary_events_controller.get_by_id(str(date))
        if entry is None:
            return None
        else:
            return entry.calendar_event_id

    def save_weekly_summary_event_id_for_date(self, event_id: str, start: datetime, end: datetime):
        """
        Save a weekly summary calendar event id so that the event can be updated at a later date if needed
        :param event_id: the calendar event id
        :param start: start of the week
        :param end: end of the week
        :return: None
        """
        entry: CalendarSummaryEvent = CalendarSummaryEvent(event_id, start, end)
        if self.user.weekly_summary_calendar_event is None or \
                self.user.weekly_summary_calendar_event.end_datetime.date() < end.date():
            self.user.weekly_summary_calendar_event = entry
            self.user_controller.update(self.user.user_id, self.user)

        self.weekly_summary_events_controller.insert(str(end.date()), entry)

    def add_summary_event_to_calendar(self, title: str, description: str, timezone: str, date: Date) -> str:
        """
        Add a new summary calendar event
        :param title: the title of the event
        :param description: the description of the event
        :param timezone: the timezone in which it should be shown as
        :param date: the date the event should be added to
        :return: the calendar event id
        """
        return self.calendar_util.add_all_day_event(title, description, timezone, str(date).replace(' ', 'T'))

    def update_summary_event_to_calendar(self, event_id: str, title: str, description: str, timezone: str, date: Date) -> str:
        """
        Update a calendar summary event
        :param event_id: the calendar event id indicating which event to update
        :param title: the new title
        :param description: the new description
        :param timezone: the local timezone it should be displayed in
        :param date: the local date the event should be displayed in
        :return: the calendar event id
        """
        return self.calendar_util.update_all_day_event(event_id, title, description, timezone, str(date).replace(' ', 'T'))

    def get_activities(self, start: datetime, end: datetime) -> [Activity]:
        """
        Get the users activities between the specified date
        :param start: start time in UTC
        :param end: end time in UTC
        :return: a list of activities that fell between the specified dates
        """
        return list(self.strava_util.get_activities(after=start, before=end))

    def get_date_in_local_timezone(self, date: datetime) -> datetime:
        """
        Convert a date to the users local timezone
        :param date: date to convert timezone of
        :return: the datettime in the users local timezone
        """
        return datetime.fromtimestamp(date.timestamp(), tz=tz.gettz(self.user_local_timezone))

    def get_activities_between_date(self, activities: [Activity], start: datetime, end: datetime) -> [Activity]:
        """
        Return a list of activities that fall between the start and end date
        :param activities: list of activities to check
        :param start: start date
        :param end: end date
        :return: list of activities that fall between the dates specified
        """
        day_activities: [Activity] = []
        for a in activities:
            activity_date_utc: datetime = datetime.fromtimestamp(a.start_date_local.timestamp(), tz=timezone.utc)
            if start < activity_date_utc < end:
                day_activities.append(a)

        return day_activities
