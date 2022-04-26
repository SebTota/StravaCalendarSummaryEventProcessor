from email.base64mime import body_decode
from strava_calendar_summary_utils import Logging

import base64
import logging

def start(event, context):
    Logging()

    if 'data' in event:
        body = base64.b64decode(event['data']).decode('utf-8')
        logging.info(body)
    else:
        logging.error('Could not find data for function: {}'.format(context.event_id))
