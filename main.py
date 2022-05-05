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
        logging.exception(
            'Error launching event processing function. Could not find data for function: {}'.format(context.event_id))
        return

    try:
        strava_event: StravaEvent = StravaEvent.from_dict(body)
    except Exception as e:
        logging.error('Failed creating Strava Event from cloud function data.')
        logging.exception(e)
        return

    logging.info('Processing event: {} for user: {}'
                 .format(strava_event.event_time, strava_event.athlete_id))

    try:
        user: User = UserController().get_by_id(str(strava_event.athlete_id))
        assert user is not None
    except Exception as e:
        logging.error('Failed getting a user for event: {} for user: {}.'
                      .format(strava_event.event_id, strava_event.athlete_id))
        logging.exception(e)
        return

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

    try:
        title_template = user.calendar_preferences.title_template
        description_template = user.calendar_preferences.description_template
    except:
        logging.error(
            'Failed to find title/description calendar event template for user: {}. Defaulting to base templates.'.format(
                user.user_id))
        title_template = DEFAULT_TITLE_TEMPLATE
        description_template = DEFAULT_DESCRIPTION_TEMPLATE

    print(str(activity.timezone))
    print(str(activity.start_date_local).replace(' ', 'T'))
    print(str((activity.start_date_local + activity.moving_time)).replace(' ', 'T'))

    cal_event_id = g_cal.add_event(TemplateBuilder.fill_template(title_template, activity),
                                   TemplateBuilder.fill_template(description_template, activity),
                                   str(activity.timezone),
                                   str(activity.start_date_local).replace(' ', 'T'),
                                   str((activity.start_date_local + activity.moving_time)).replace(' ', 'T'))

    cal_event: CalendarEvent = CalendarEvent(activity.id, cal_event_id, title_template, description_template)
    CalendarEventController(user.user_id).insert(activity.id, cal_event)


def update_activity_event(strava_event: StravaEvent, user: User):
    print('TODO')


def delete_activity_event(strava_event: StravaEvent, user: User):
    print('TODO')


if __name__ == '__main__':
    user: User = UserController().get_by_id('10000566')
    strava_event = StravaEvent('activity', 6998137422, StravaEventType.CREATE, {}, 10000566, 0)
    new_activity_event(strava_event, user)
