class StravaAuthUser:
    def __init__(self, username, access_token, refresh_token, token_expires_at, last_sync):
        self.username = username
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_expires_at = token_expires_at
        self.last_sync = last_sync
