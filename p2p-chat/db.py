from pymongo import MongoClient


# Includes database operations
class DB:

    # db initializations
    def __init__(self):
        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client['p2p-chat']

    # checks if an account with the username exists
    def is_account_exist(self, username):

        if self.db.accounts.count_documents({'username': username}) > 0:
            return True
        else:
            return False

    # registers a user
    def register(self, username, password):
        account = {
            "username": username,
            "password": password
        }
        self.db.accounts.insert_one(account)

    # retrieves the password for a given username
    def get_password(self, username):
        return self.db.accounts.find_one({"username": username})["password"]

    # checks if an account with the username online
    def is_account_online(self, username):
        if self.db.online_peers.count_documents({"username": username}) > 0:
            return True
        else:
            return False

    # logs in the user
    def user_login(self, username, ip, TCP_port, UDP_port):
        online_peer = {
            "username": username,
            "ip": ip,
            "TCP_Port": TCP_port,
            "UDP_Port": UDP_port

        }
        self.db.online_peers.insert_one(online_peer)

    # logs out the user
    def user_logout(self, username):
        self.db.online_peers.delete_one({"username": username})

    # retrieves the ip address and the port number of the username
    def get_peer_ip_port(self, username):
        res = self.db.online_peers.find_one({"username": username})
        return res["ip"], res["TCP_Port"]

    def get_peer_ip_udp_port(self, username):
        res = self.db.online_peers.find_one({"username": username})
        return res["ip"], res["UDP_Port"]

    def user_leave_room(self, room_id, username):
        room_query = {'Room_id': room_id}
        user_query = {'username': username}
        update_query = {'$pull': {'users': user_query}}

        self.rooms_collection.update_one(room_query, update_query)

    def is_tcp_port_taken(self, tcp_port):
        if self.db.online_peers.count_documents({"TCP_Port": str(tcp_port)}) > 0:
            return True
        else:
            return False

    # checks if a UDP port number is taken by an online peer
    def is_udp_port_taken(self, udp_port):
        if self.db.online_peers.count_documents({"UDP_Port": str(udp_port)}) > 0:
            return True
        else:
            return False
