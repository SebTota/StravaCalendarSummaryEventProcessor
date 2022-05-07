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
        activity_event(strava_event, user, update=True)
    elif strava_event.event_type == StravaEventType.CREATE.value:
        activity_event(strava_event, user)
    elif strava_event.event_type == StravaEventType.DELETE.value:
        delete_activity_event(strava_event, user)
    else:
        logging.error('Received a request that the event processor doesnt know how to handle. Event type: {}'
                      .format(strava_event.event_type))


def app_deauthentication_event(strava_event: StravaEvent, user: User):
    logging.info('Removing user: {} due to de-authentication event from Strava'.format(user.user_id))
    # TODO: Remove all information related to user
    UserController().delete(user.user_id)


def activity_event(strava_event: StravaEvent, user: User, update: bool = False):
    default_title_template = '{name}'
    default_description_template = 'Strava activity: {type}. \nDistance: {distance_miles}\nDuration: {duration}'

    strava_util: StravaUtil = StravaUtil(user.strava_credentials, user)
    cal_util = GoogleCalendarUtil(user.calendar_credentials, user=user, calendar_id=user.calendar_id)
    cal_event_controller = CalendarEventController(user.user_id)

    activity: Activity = strava_util.get_activity(strava_event.event_id)
    assert activity is not None

    if user.calendar_preferences and user.calendar_preferences.title_template:
        title_template = user.calendar_preferences.title_template
    else:
        title_template = default_title_template

    if user.calendar_preferences and user.calendar_preferences.description_template:
        description_template = user.calendar_preferences.description_template
    else:
        description_template = default_description_template

    if update:
        # Update an existing calendar event and save the new calendar event id
        cal_event: CalendarEvent = cal_event_controller.get_by_id(str(strava_event.event_id))

        if cal_event is None:
            # Although this was an update event, this is an update for an event we have not yet processed. Treat
            # this as a new activity event instead
            logging.info('Received an update event on an activity we never processed. Treating activity: {} from '
                         'user: {} as new activity event.'.format(strava_event.event_id, strava_event.athlete_id))
            update = False
        else:

            # Use the templates that were used on the initial event creation
            title_template = cal_event.title_template
            description_template = cal_event.description_template

            cal_util.update_event(cal_event.calendar_event_id,
                                  TemplateBuilder.fill_template(title_template, activity),
                                  TemplateBuilder.fill_template(description_template, activity),
                                  str(activity.timezone),
                                  str(activity.start_date_local).replace(' ', 'T'),
                                  str((activity.start_date_local + activity.moving_time)).replace(' ', 'T'))

    if not update:
        # Create a new calendar event for this strava event
        cal_event_id = cal_util.add_event(TemplateBuilder.fill_template(title_template, activity),
                                          TemplateBuilder.fill_template(description_template, activity),
                                          str(activity.timezone),
                                          str(activity.start_date_local).replace(' ', 'T'),
                                          str((activity.start_date_local + activity.moving_time)).replace(' ', 'T'))
        cal_event: CalendarEvent = CalendarEvent(activity.id, cal_event_id, title_template, description_template)
        cal_event_controller.insert(activity.id, cal_event)


def delete_activity_event(strava_event: StravaEvent, user: User):
    g_cal = GoogleCalendarUtil(user.calendar_credentials, user=user, calendar_id=user.calendar_id)
    cal_event: CalendarEvent = CalendarEventController(user.user_id).get_by_id(str(strava_event.event_id))
    if cal_event is None:
        return  # Skip delete events for activities that were never processed
    g_cal.delete_event(cal_event.calendar_event_id)
