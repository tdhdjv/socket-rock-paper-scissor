import socket
import json
import selectors
from protocols import Protocols
from room import Room
from types import SimpleNamespace

class Server:

    rooms:list[Room] = []
    running = True
    active_clients:list[socket.socket] = []
    waiting_clients:dict[socket.socket, int] = {}
    request_queue:list[tuple] = []
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
        
        while self.running:
            #checks for an io streams
            event = self.sel.select(timeout=None)
            for key, mask in event:
                data = key.data
                sock = key.fileobj
                #if the data is None that means it's a server socket
                if data == None:
                    self.accept_clients(sock)
                else:
                    #client socket
                    self.handle_client(sock, data, mask)
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
        room = Room(self.waiting_clients)
        self.rooms.append(room)

        #register all the clients
        for conn in self.waiting_clients.keys():
            id = self.waiting_clients[conn]

            conn.setblocking(False)
            #assign a client id
            conn.send(str(id).encode('utf-8'))
            data = SimpleNamespace(id = id, room = room)

            self.active_clients.append(conn)
            self.sel.register(conn, selectors.EVENT_READ | selectors.EVENT_WRITE, data = data)

        #clear waiting_clients
        self.waiting_clients = {}

    def delete_room(self, room: Room):
        #kick every client in that room
        copy = room.clients.copy()
        for client in  copy:
            kick_message = {'r_type': Protocols.Response.COMMAND, 'data': 'quit'}
            self.send(client, json.dumps(kick_message).encode('utf-8'))
            #remove the connection from the client
            self.remove_client(client, room)
        #delete room
        del(room)
    
    def handle_client(self, conn:socket.SocketType, data: SimpleNamespace, mask) -> None:
        #check if the room can still exist
        room:Room = data.room

        if len(room.clients) < room.MIN_CLIENT_NUM:
            self.delete_room(room)
            return

        if mask & selectors.EVENT_READ:
            self.handle_recieving(conn, data)
        if mask & selectors.EVENT_WRITE:
            self.handle_sending()
    
    def handle_recieving(self, conn:socket.socket, data:SimpleNamespace) -> None:
        
        room:Room = data.room

        request = conn.recv(1024)
        if request:
            #handle recieving data
            json_data = json.loads(request.decode('utf-8'))
            room.handle_data(conn, json_data)

            #sending gamestate to room
            self.request_queue.append((json.dumps(room.get_response()).encode('utf-8'), room.get_request_reciever()))
            
        else:
            self.remove_client(conn, room)
           
    def handle_sending(self) -> None:
        if self.request_queue:
            request = self.request_queue.pop(0)
            data = request[0]
            recieving_clients = request[1]
            self.broadcast_group(recieving_clients, data)

    def send(self, conn:socket.socket, message:bytes) -> None:
        conn.send(message)

    def broadcast(self, sender:socket.socket, message:bytes) -> None:
        'sends message to everyone except sender'
        for conn in self.active_clients:
            if conn == sender:
                continue
            self.send(conn, message)

    def broadcast_group(self, group:list[socket.socket], message:bytes) -> None:
        'sends message to everyone in a group'
        for conn in group:
            self.send(conn, message)

    def remove_client(self, conn:socket.socket, room:Room):
        #remove the connection from the client
        room.remove_client(conn)
        #client has disconnected
        conn.close()
        self.active_clients.remove(conn)
        self.sel.unregister(conn)

        #server closing
        if len(self.active_clients) <= 0:
            self.running = False
        
if __name__ == "__main__":
    server = Server()
    server.run()