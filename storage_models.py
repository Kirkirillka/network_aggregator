from mongoengine import *

ADDRESS = "address"
NETWORK = "network"


class NetworkEntry(Document):
    value = StringField(primary_key=True)
    type = StringField(choices=[ADDRESS, NETWORK], required=True)
    supernet = ReferenceField('self')
    children = ListField(ReferenceField('self'))
