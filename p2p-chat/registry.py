from pymongo import MongoClient
from socket import *
import threading
import select
import logging
import db
import chatroomsdb
import ast


# This class is used to process the peer messages sent to registry
# for each peer connected to registry, a new client thread is created
class ClientThread(threading.Thread):
    # initializations for client thread
    def __init__(self, ip, port_num, tcp_client_socket):
        threading.Thread.__init__(self)
        # ip of the connected peer
        self.ip = ip
        # port number of the connected peer
        self.port = port_num
        # socket of the peer
        self.tcpClientSocket = tcp_client_socket
        # username, online status and udp server initializations
        self.username = None
        self.isOnline = True
        self.udpServer = None
        print("New thread started for " + ip + ":" + str(port_num))

    # main of the thread
    def run(self):
        # locks for thread which will be used for thread synchronization
        self.lock = threading.Lock()
        print("Connection from: " + self.ip + ":" + str(port))
        print("IP Connected: " + self.ip)

        while True:
            try:
                # waits for incoming messages from peers
                message_ = self.tcpClientSocket.recv(1024).decode().split()
                logging.info("Received from " + self.ip + ":" + str(self.port) + " -> " + " ".join(message_))
                #   JOIN    #
                if message_[0] == "JOIN":
                    # join-exist is sent to peer,
                    # if an account with this username already exists
                    if db.is_account_exist(message_[1]):
                        response = "join-exist"
                        print("From-> " + self.ip + ":" + str(self.port) + " " + response)
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)
                        self.tcpClientSocket.send(response.encode())
                    # join-success is sent to peer,
                    # if an account with this username is not exist, and the account is created
                    else:
                        db.register(message_[1], message_[2])
                        response = "join-success"
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)
                        self.tcpClientSocket.send(response.encode())
                #   LOGIN    #
                elif message_[0] == "LOGIN":
                    # login-account-not-exist is sent to peer,
                    # if an account with the username does not exist
                    if not db.is_account_exist(message_[1]):
                        response = "login-account-not-exist"
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)
                        self.tcpClientSocket.send(response.encode())
                    # login-online is sent to peer,
                    # if an account with the username already online
                    elif db.is_account_online(message_[1]):
                        response = "login-online"
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)
                        self.tcpClientSocket.send(response.encode())
                    # login-success is sent to peer,
                    # if an account with the username exists and not online
                    else:
                        # retrieves the account's password, and checks if the one entered by the user is correct
                        retrievedPass = db.get_password(message_[1])
                        # if password is correct, then peer's thread is added to threads list
                        # peer is added to db with its username, port number, and ip address
                        if retrievedPass == message_[2]:
                            self.username = message_[1]
                            self.lock.acquire()
                            try:
                                tcpThreads[self.username] = self
                            finally:
                                self.lock.release()

                            db.user_login(message_[1], self.ip, message_[3], message_[4])
                            # login-success is sent to peer,
                            # and an udp server thread is created for this peer, and thread is started
                            # timer thread of the udp server is started
                            response = "login-success"
                            logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)
                            self.tcpClientSocket.send(response.encode())
                            self.udpServer = UDPServer(self.username, self.tcpClientSocket)
                            self.udpServer.start()
                            self.udpServer.timer.start()
                        # if password not matches and then login-wrong-password response is sent
                        else:
                            response = "login-wrong-password"
                            logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)
                            self.tcpClientSocket.send(response.encode())
                #   LOGOUT  #
                elif message_[0] == "LOGOUT":
                    # if user is online,
                    # removes the user from onlinePeers list
                    # and removes the thread for this user from tcpThreads
                    # socket is closed and timer thread of the udp for this
                    # user is cancelled
                    if len(message_) > 1 and message_[1] is not None and db.is_account_online(message_[1]):
                        db.user_logout(message_[1])
                        self.lock.acquire()
                        try:
                            if message_[1] in tcpThreads:
                                del tcpThreads[message_[1]]
                        finally:
                            self.lock.release()
                        print(self.ip + ":" + str(self.port) + " is logged out")
                        self.tcpClientSocket.close()
                        self.udpServer.timer.cancel()
                        break
                    else:
                        self.tcpClientSocket.close()
                        break
                #   SEARCH  #
                elif message_[0] == "SEARCH":
                    # checks if an account with the username exists
                    if db.is_account_exist(message_[1]):
                        # checks if the account is online
                        # and sends the related response to peer
                        if db.is_account_online(message_[1]):
                            peer_info = db.get_peer_ip_port(message_[1])
                            response = "search-success " + peer_info[0] + ":" + peer_info[1]
                            logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)
                            self.tcpClientSocket.send(response.encode())
                        else:
                            response = "search-user-not-online"
                            logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)
                            self.tcpClientSocket.send(response.encode())
                    # enters if username does not exist
                    else:
                        response = "search-user-not-found"
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)
                        self.tcpClientSocket.send(response.encode())

                elif message_[0] == "CREATEROOM":

                    ChatDB.create_room(message_[1])
                    response = "room-created"
                    logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)
                    self.tcpClientSocket.send(response.encode())

                elif message_[0] == "SHOWROOMS":
                    response = ChatDB.get_available_rooms()
                    logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + str(response))
                    self.tcpClientSocket.send(str(response).encode())

                elif message_[0] == "GETID":
                    response = ChatDB.get_available_room_ids()
                    logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + str(response))
                    self.tcpClientSocket.send(str(response).encode())

                elif message_[0] == "CHECKINROOM":
                    ChatDB.join_room(int(message_[1]), message_[2])
                    response = "join-success"
                    logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)
                    self.tcpClientSocket.send(response.encode())

                elif message_[0] == "ROOM_USERS":
                    response = ChatDB.get_users_in_room(int(message_[1]))
                    logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + str(response))
                    self.tcpClientSocket.send(str(response).encode())

                elif message_[0] == "ONLINE_USER?":
                    response = db.is_account_online(message_[1])
                    logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + str(response))
                    self.tcpClientSocket.send(str(response).encode())

                elif message_[0] == "ip&UDP_PORT":
                    response = db.get_peer_ip_udp_port(message_[1])
                    logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + str(response))
                    self.tcpClientSocket.send(str(response).encode())

                elif message_[0] == "show_USER_ROOMS":
                    response = ChatDB.get_rooms_for_user(message_[1])
                    logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + str(response))
                    self.tcpClientSocket.send(str(response).encode())

                elif message_[0] == "user_in_room?":
                    response = ChatDB.is_user_in_room(int(message_[1]), message_[2])
                    logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + str(response))
                    self.tcpClientSocket.send(str(response).encode())

                elif message_[0] == "LEAVEROOM":
                    ChatDB.user_leave_room(int(message_[1]), message_[2])
                    response = "Leaving room successfully.."
                    logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)
                    self.tcpClientSocket.send(response.encode())

            except OSError as oErr:
                logging.error("OSError: {0}".format(oErr))

    # function for resetting the timeout for the udp timer thread
    def resetTimeout(self):
        self.udpServer.resetTimer()


# implementation of the udp server thread for clients
class UDPServer(threading.Thread):

    # udp server thread initializations
    def __init__(self, username, clientSocket):
        threading.Thread.__init__(self)
        self.username = username
        # timer thread for the udp server is initialized
        self.timer = threading.Timer(3, self.waitHelloMessage)
        self.tcpClientSocket = clientSocket

    # if hello message is not received before timeout
    # then peer is disconnected
    def waitHelloMessage(self):
        if self.username is not None:
            db.user_logout(self.username)
            if self.username in tcpThreads:
                del tcpThreads[self.username]
        self.tcpClientSocket.close()
        print("Removed " + self.username + " from online peers")

    # resets the timer for udp server
    def resetTimer(self):
        self.timer.cancel()
        self.timer = threading.Timer(23, self.waitHelloMessage)
        self.timer.start()


# tcp and udp server port initializations
print("Registry started...")
port = 15600
portUDP = 15500

# db initialization

ChatDB = chatroomsdb.ChatroomsDB()
db = db.DB()

# gets the ip address of this peer
# first checks to get it for Windows devices
# if the device that runs this application is not windows
# it checks to get it for macOS devices
hostname = gethostname()
try:
    host = gethostbyname(hostname)
except gaierror:
    import netifaces as ni

    host = ni.ifaddresses('en0')[ni.AF_INET][0]['addr']

print("Registry IP address: " + host)
print("Registry port number: " + str(port))

# onlinePeers list for online account
onlinePeers = {}
# accounts list for accounts
accounts = {}
# tcpThreads list for online client's thread
tcpThreads = {}

# tcp and udp socket initializations
tcpSocket = socket(AF_INET, SOCK_STREAM)
udpSocket = socket(AF_INET, SOCK_DGRAM)
tcpSocket.bind((host, port))
udpSocket.bind((host, portUDP))
tcpSocket.listen(5)

# input sockets that are listened
inputs = [tcpSocket, udpSocket]

# log file initialization
logging.basicConfig(filename="registry.log", level=logging.INFO)

# as long as at least a socket exists to listen registry runs
while inputs:

    print("Listening for incoming connections...")
    # monitors for the incoming connections
    readable, writable, exceptional = select.select(inputs, [], [])
    for s in readable:
        # if the message received comes to the tcp socket
        # the connection is accepted and a thread is created for it, and that thread is started
        if s is tcpSocket:
            tcpClientSocket, addr = tcpSocket.accept()
            newThread = ClientThread(addr[0], addr[1], tcpClientSocket)
            newThread.start()
        # if the message received comes to the udp socket
        elif s is udpSocket:
            # received the incoming udp message and parses it
            message, clientAddress = s.recvfrom(1024)
            message = message.decode().split()
            # checks if it is a hello message
            if message[0] == "HELLO":
                # checks if the account that this hello message 
                # is sent from is online
                if message[1] in tcpThreads:
                    # resets the timeout for that peer since the hello message is received
                    tcpThreads[message[1]].resetTimeout()
                    print("Hello is received from " + message[1])
                    logging.info(
                        "Received from " + clientAddress[0] + ":" + str(clientAddress[1]) + " -> " + " ".join(message))

# registry tcp socket is closed
tcpSocket.close()
