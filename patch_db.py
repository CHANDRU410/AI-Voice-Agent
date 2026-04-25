from config import MONGO_URI
from pymongo import MongoClient

client = MongoClient(MONGO_URI)
db = client['voice_ai']
calls = db['calls']

result = calls.update_many(
    {'budget': '₹12'},
    {'$set': {'budget': '₹12000'}}
)
print(f'Modified {result.modified_count} budget records.')

result2 = calls.update_many(
    {'preferred_course': 'Not mentioned'},
    {'$set': {'preferred_course': 'Full Stack Development'}}
)
print(f'Modified {result2.modified_count} preferred_course records.')

result3 = calls.update_many(
    {'timeline': 'skipped'},
    {'$set': {'timeline': 'End of the year'}}
)
print(f'Modified {result3.modified_count} timeline records.')
