from pymongo import MongoClient

uri = "mongodb+srv://sk:12345@aiagent.ih6eyvt.mongodb.net/voice_ai"

client = MongoClient(uri)

print(client.server_info())