from tinydb import TinyDB, Query
from flask import Flask
import datetime

from strava_auth_user import StravaAuthUser
from strava import Strava

USER = 'sebtota'

db = TinyDB('db.json')
user_table = db.table('stravaUserAuth')


def save_user_strava_auth(user_auth: StravaAuthUser) -> None:
    user_table.insert(user_auth.__dict__)


def get_user_strava_auth(username: str) -> StravaAuthUser:
    q = Query()
    return StravaAuthUser(**(user_table.search(q.username == username))[0])


if __name__ == '__main__':
    print('Running Strava Private Run')
    user = get_user_strava_auth(USER)
    api = Strava(strava_auth_user=user)
    print(api.get_activity(7008891832))
    # activities = api.get_activities(after=datetime.datetime(2022, 4, 18))
    # for activity in activities:
    #     print(api.get_activity(activity.id).)
    #     print(activity.id)
