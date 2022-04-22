class User:
    def __init__(self, user_id, access_token, refresh_token, token_expires_at):
        self.user_id = user_id
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_expires_at = token_expires_at

    @staticmethod
    def from_dict(source):
        return User(**source)

    def to_dict(self):
        return self.__dict__
