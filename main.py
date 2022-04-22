import functions_framework
from flask import Flask
from user import User
from strava import Strava
from config import STRAVA_WEBHOOK
import db

# NOT SENSITIVE
USER_ID = 7008891832

def get_webhook(request):
    print("GET /webhook")
    data = request.args

    if 'hub.mode' in data and 'hub.verify_token' in data:
        if data['hub.mode'] == 'subscribe' and data['hub.verify_token'] == STRAVA_WEBHOOK['VERIFY_TOKEN']:
            print('WEBHOOK_VERIFIED')
            return {'hub.challenge': data['hub.challenge']}, 200
        else:
            return '', 403


def post_webhook(request):
    print("POST /webhook")
    data = request.args

    # On new activity creation
    if 'object_type' in data and 'aspect_type' in data \
        and data['object_type'] == 'activity':
        # and data['aspect_type'] == 'create'

        user_id = data['owner_id']
        activity_id = data['object_id']

        print('Received a new activity: {} event for user: {}'.format(activity_id, user_id))

    return 'EVENT_RECEIVED'


def test(request):
    print("/test")

    user = db.get_user(USER_ID)
    return {'test_user': user.user_id}



@functions_framework.http
def start(request):

    print("Path: " + request.path)
    print("Method: " + request.method)

    if request.path == '/test':
        return test(request)

    if request.path == '/webhook':
        if request.method == 'GET':
            return get_webhook(request)
        if request.method == 'POST':
            return post_webhook(request)

    return "Did not find endpoint"
