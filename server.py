import socket
import json
import selectors
from room import Room
from typing import Any
from types import SimpleNamespace

class Server:

    room = None
    running = True
    active_clients:list[socket.socket] = []
    waiting_clients:dict[socket.socket, int] = {}
    client_ID = 1

    def run(self, host='127.0.0.1', port=1234) -> None:
        #socket configs
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((host, port))
        server.setblocking(False)
        server.listen()
        print(f'Connected to {host}: {port}')

        #config selector
        self.sel = selectors.DefaultSelector()
        self.sel.register(server, selectors.EVENT_READ, data = None)
        
        #checks for an io streams
        while self.running:
            event = self.sel.select(timeout=None)
            for key, _ in event:
                data = key.data
                sock = key.fileobj
                #if the data is None that means it's a server socket
                if data == None:
                    self.accept_clients(sock)
                else:
                    #client socket
                    self.handle_client(sock, data)
        server.close()
        self.sel.close()
        
    def accept_clients(self, server_sock: socket.socket) -> None:
        conn, addr = server_sock.accept()
        print(f'Connected to {str(addr)}')

        self.waiting_clients[conn] = self.client_ID
        self.client_ID += 1

        #if the waiting_client list is more or equal to the min client required then create a room
        if len(self.waiting_clients) >= Room.MIN_CLIENT_NUM:
            self.create_room()
    
    def create_room(self):
        print('Creating new room')
        #create a new room with all the clients
        self.room = Room(self.waiting_clients)

        #register all the clients
        for conn in self.waiting_clients.keys():
            id = self.waiting_clients[conn]

            conn.setblocking(False)
            #assign a client id
            conn.send(str(id).encode('utf-8'))
            data = SimpleNamespace(id = id, room = self.room)

            self.active_clients.append(conn)
            self.sel.register(conn, selectors.EVENT_READ, data = data)

        #clear waiting_clients
        self.waiting_clients = {}
        
    def handle_client(self, conn:socket.SocketType, data: SimpleNamespace) -> None:

        room:Room = data.room

        request = conn.recv(1024)
        if request:
            #handle recieving data
            json_data = json.loads(request.decode('utf-8'))
            room.handle_data(conn, json_data)

            #sending gamestate to room
            self.broadcast_group(room.get_request_reciever(), json.dumps(room.get_response()).encode('utf-8'))
            
        else:
            #remove the connection from the client
            room.remove_client(conn)
            #client has disconnected
            conn.close()
            self.active_clients.remove(conn)
            self.sel.unregister(conn)

            #server closing
            if len(self.active_clients) <= 0:
                self.running = False
    
    def send(self, conn:socket.socket, message:bytes) -> None:
        conn.send(message)

    def broadcast(self, sender:socket.socket, message:bytes) -> None:
        'sends message to everyone except sender'
        for conn in self.active_clients:
            if conn == sender:
                continue
            self.send(conn, message)

    def broadcast_group(self, group:list[socket.socket], message:bytes) -> None:
        'sends message to everyone in a group except sender'
        for conn in group:
            self.send(conn, message)

if __name__ == "__main__":
    server = Server()
    server.run()