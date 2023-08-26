from pymongo import MongoClient

class ChatroomsDB:
    def __init__(self):
        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client['ChatRooms']
        self.rooms_collection = self.db["ROOMS"]
        self.room_counter = self.get_room_counter()

    def get_room_counter(self):
        counter = self.db["counter"].find_one({"_id": "room_id_counter"})
        if counter:
            return counter["count"]
        else:
            self.db["counter"].insert_one({"_id": "room_id_counter", "count": 0})
            return 0

    def update_room_counter(self):
        self.db["counter"].update_one({"_id": "room_id_counter"}, {"$inc": {"count": 1}})
        counter = self.db["counter"].find_one({"_id": "room_id_counter"})
        self.room_counter = counter["count"]

    def create_room(self, name):
        query_name = {'Room_Name': name}
        existing_room = self.rooms_collection.find_one(query_name)
        if existing_room:
            print(f"A room with the name '{name}' already exists.")
        else:
            room_id = self.room_counter + 1
            self.update_room_counter()
            room_data = {'Room_id': room_id, 'Room_Name': name, 'users': []}
            self.rooms_collection.insert_one(room_data)
            print(f"Room '{name}' with ID {room_id} created successfully.")

    def is_user_in_room(self, room_id, username):
        query = {'Room_id': room_id, 'users.username': username}
        return self.rooms_collection.count_documents(query) > 0

    def join_room(self, room_id, username):
        room_query = {'Room_id': room_id}
        user_query = {'username': username}
        update_query = {'$addToSet': {'users': user_query}}

        self.rooms_collection.update_one(room_query, update_query)

    def user_leave_room(self, room_id, username):
        room_query = {'Room_id': room_id}
        user_query = {'username': username}
        update_query = {'$pull': {'users': user_query}}

        self.rooms_collection.update_one(room_query, update_query)

    def get_available_rooms(self):
        projection = {'Room_id': 1, 'Room_Name': 1, '_id': 0}
        return list(self.rooms_collection.find({}, projection))

    def get_available_room_ids(self):
        projection = {'Room_id': 1, '_id': 0}
        rooms = self.rooms_collection.find({}, projection)
        room_ids = [room['Room_id'] for room in rooms]
        return room_ids


    def get_users_in_room(self, room_id):
        query = {'Room_id': room_id}
        projection = {'users.username': 1, '_id': 0}
        room = self.rooms_collection.find_one(query, projection)
        if room:
            users = room.get('users', [])
            usernames = [user['username'] for user in users]
            return usernames
        else:
            return []

    def get_rooms_for_user(self, username):
        query = {'users.username': username}
        projection = {'Room_id': 1, 'Room_Name': 1, '_id': 0}
        return list(self.rooms_collection.find(query, projection))



"""
TEMP = ChatroomsDB()
print(TEMP.get_rooms_for_user("mostafa"))
print(TEMP.create_room("mostafa"))
print(TEMP.is_user_in_room(1, "me"))
TEMP.join_room(1, "me")
print(TEMP.is_user_in_room(1, "me"))
print(TEMP.get_available_rooms())
print(TEMP.get_users_in_room(1))
TEMP.join_room(1, "H")
print(TEMP.get_users_in_room(1))
"""
