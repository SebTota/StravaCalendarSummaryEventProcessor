from strava_calendar_summary_utils import Logging, StravaUtil, GoogleCalendarUtil, TemplateBuilder
from strava_calendar_summary_data_access_layer import StravaEvent, User, UserController, \
    StravaEventType, StravaEventUpdateType, CalendarEventController, CalendarEvent

import logging
import base64
import json
from stravalib.model import Activity


def start(event, context):
    Logging()

    if 'data' in event:
        body = json.loads(base64.b64decode(event['data']).decode('utf-8'))
    else:
        logging.error(
            'Error launching event processing function. Could not find data for function: {}'.format(context.event_id))
        return

    try:
        strava_event: StravaEvent = StravaEvent.from_dict(body)
    except Exception as e:
        logging.error('Failed creating Strava Event from cloud function data.')
        raise e

    logging.info('Processing event: {} for user: {}'
                 .format(strava_event.event_time, strava_event.athlete_id))

    try:
        user: User = UserController().get_by_id(str(strava_event.athlete_id))
        assert user is not None
    except Exception as e:
        logging.error('Failed getting a user for event: {} for user: {}.'
                      .format(strava_event.event_id, strava_event.athlete_id))
        raise e

    if strava_event.object_type == 'athlete' and strava_event.event_type == StravaEventType.UPDATE \
            and StravaEventUpdateType.AUTHORIZED in strava_event.updates and \
            strava_event.updates[StravaEventUpdateType.AUTHORIZED] == 'false':
        # App de-authentication request
        app_deauthentication_event(strava_event, user)
        return

    if strava_event.object_type != 'activity': return  # Ignore all non 'activity' events other than de-auth events

    if strava_event.event_type == StravaEventType.UPDATE.value:
        update_activity_event(strava_event, user)
    elif strava_event.event_type == StravaEventType.CREATE.value:
        new_activity_event(strava_event, user)
    elif strava_event.event_type == StravaEventType.DELETE.value:
        delete_activity_event(strava_event, user)
    else:
        logging.error('Received a request that the event processor doesnt know how to handle. Event type: {}'
                      .format(strava_event.event_type))


def app_deauthentication_event(strava_event: StravaEvent, user: User):
    logging.info('Removing user: {} due to de-authentication event from Strava'.format(user.user_id))
    # TODO: Remove all information related to user
    UserController().delete(user.user_id)


def new_activity_event(strava_event: StravaEvent, user: User):
    DEFAULT_TITLE_TEMPLATE = '{name}'
    DEFAULT_DESCRIPTION_TEMPLATE = 'Strava activity: {type}. \nDistance: {distance_miles}\nDuration: {duration}'

    strava_util: StravaUtil = StravaUtil(user.strava_credentials, user)
    g_cal = GoogleCalendarUtil(user.calendar_credentials, user=user, calendar_id=user.calendar_id)
    activity: Activity = strava_util.get_activity(strava_event.event_id)
    assert activity is not None

    if user.calendar_preferences and user.calendar_preferences.title_template != '':
        title_template = user.calendar_preferences.title_template
    else:
        title_template = DEFAULT_TITLE_TEMPLATE

    if user.calendar_preferences and user.calendar_preferences.description_template != '':
        description_template = user.calendar_preferences.description_template
    else:
        description_template = DEFAULT_DESCRIPTION_TEMPLATE

    cal_event_id = g_cal.add_event(TemplateBuilder.fill_template(title_template, activity),
                                   TemplateBuilder.fill_template(description_template, activity),
                                   str(activity.timezone),
                                   str(activity.start_date_local).replace(' ', 'T'),
                                   str((activity.start_date_local + activity.moving_time)).replace(' ', 'T'))

    cal_event: CalendarEvent = CalendarEvent(activity.id, cal_event_id, title_template, description_template)
    CalendarEventController(user.user_id).insert(activity.id, cal_event)


def update_activity_event(strava_event: StravaEvent, user: User):
    # TODO: Make this more efficient. This should be as simple as modifying the new event function
    #  to support insert and update API calls
    delete_activity_event(strava_event, user)
    new_activity_event(strava_event, user)


def delete_activity_event(strava_event: StravaEvent, user: User):
    g_cal = GoogleCalendarUtil(user.calendar_credentials, user=user, calendar_id=user.calendar_id)
    cal_event: CalendarEvent = CalendarEventController(user.user_id).get_by_id(str(strava_event.event_id))
    if cal_event is None:
        return  # Skip delete events for activities that were never processed
    g_cal.delete_event(cal_event.calendar_event_id)


# if __name__ == '__main__':
#     user: User = UserController().get_by_id('10000566')
#     strava_event = StravaEvent('activity', 6998137422, StravaEventType.CREATE, {}, 10000566, 0)
#     new_activity_event(strava_event, user)
