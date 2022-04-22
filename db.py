from user import User
from google.cloud import firestore

db = firestore.Client()
user_table = db.collection(u'Users')

def save_user(user: User) -> None:
    doc_ref = user_table.document(str(user.user_id))
    doc_ref.set(user.to_dict())

def get_user(user_id: str) -> User:
    doc_ref = user_table.document(str(user_id))
    doc = doc_ref.get()
    if doc.exists:
        return User.from_dict(doc.to_dict())
    else:
        return None
