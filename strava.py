from user import User
from stravalib.client import Client
from config import STRAVA_API
import db

import time

class Strava:
    def __init__(self, user: User):
        self.user = user
        self.init_strava_client()
        
    def init_strava_client(self):
        self.client = Client()
        self.client.access_token = self.user.access_token
        self.client.refresh_token = self.user.refresh_token
        self.client.token_expires_at = self.user.token_expires_at

    def before_api_call(self) -> None:
        self.update_access_token_if_necessary()

    def update_access_token_if_necessary(self) -> None:
        if time.time() > self.client.token_expires_at:
            refresh_response = self.client.refresh_access_token(
                client_id=STRAVA_API['STRAVA_CLIENT_ID'], 
                client_secret=STRAVA_API['STRAVA_CLIENT_SECRET'],
                refresh_token=self.client.refresh_token)

            self.user.access_token = refresh_response['access_token']
            self.user.refresh_token = refresh_response['refresh_token']
            self.user.expires_at = refresh_response['expires_at']
            db.save_user(self.user)

    def get_athlete(self):
        self.before_api_call()
        return self.client.get_athlete()

    def get_activities(self, before=None, after=None, limit=None):
        self.before_api_call()
        return self.client.get_activities(before, after, limit)

    def get_activity(self, activity_id):
        self.before_api_call()
        return self.client.get_activity(activity_id=activity_id)
