from email.base64mime import body_decode
from strava_calendar_summary_utils import Logging, StravaUtil
from strava_calendar_summary_data_access_layer import StravaEvent, User, UserController

import base64
import logging

def start(event, context):
    Logging()

    if 'data' in event:
        body = base64.b64decode(event['data']).decode('utf-8')
    else:
        logging.error('Error launching event processing function. \
            Could not find data for function: {}'.format(context.event_id))

    try:
        strava_event: StravaEvent = StravaEvent.from_dict(body)
    except Exception as e:
        logging.error('Failed creating Strava Event from cloud function data.')
        logging.exception(e)

    logging.info('Event processing function starting to process \
        event: {} for user: {}'.format(strava_event.object_id, strava_event.athlete_id))

    try:
        user: User = UserController().get_by_id(strava_event.athlete_id)
    except Exception as e:
        logging.error('Failed getting a user for \
            event: {} for user: {}.'.format(strava_event.id, strava_event.athlete_id))
        logging.exception(e)
    
    strava_util: StravaUtil = StravaUtil(user)
    activity = strava_util.get_activity(strava_event.id)

    logging.info('Adding new event to calendar')
