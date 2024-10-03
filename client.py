import socket
import json
import cmd_control
import time
from threading import Thread
from protocols import Protocols

class Client:
    
    id = -1
    running = True
    played = False
    gameOver = False

    def run(self, host='127.0.0.1', port=1234) -> None:
        #clear all the screen
        cmd_control.clear_all()

        #configs sockets
        self.client = socket.socket()
        self.client.connect((host, port))
        recieve_thread = Thread(target=self.recieve)
        send_thread = Thread(target=self.send, daemon=True)

        print('Waiting to join a room...')
        
        #get client ID
        self.id = int(self.client.recv(1024).decode('utf-8'))
        print(f'Client ID is {self.id}')
        print('Joinied a room')

        recieve_thread.start()
        send_thread.start()

        recieve_thread.join()

        self.client.close()

    def recieve(self):
        while self.running:
            response = self.client.recv(1024)
            response = response.decode('utf-8')
            message = json.loads(response)

            r_type = message['r_type']
            data = message['data']
            if r_type == Protocols.Response.COMMAND:
                if data == 'quit':
                    self.close()
            if r_type == Protocols.Response.MESSAGE:
                print(data)
            if r_type == Protocols.Response.GAMESTATE:
                cmd_control.clear_all()

                final_winner = data['final_winner']
                winners = data['winner_ids']
                scores = data['scores']
                plays:dict = data['plays']

                if final_winner != -1:
                    if final_winner == self.id:
                        print('YOU WON!!!')
                    else:
                        print('YOU LOST')
                    self.gameOver = True
                    continue
                
                for key, value in plays.items():
                    print(f'<ClientID: {key}> played: {value}')
                for key, value in plays.items():
                    print(f'<ClientID: {key}> scoreL: {scores[key]}')
                
                #print the game outcome
                if -1 in winners:
                    print('Tie!')
                elif self.id in winners:
                    print('You Win!')
                else:
                    print('You Lose!')

                #CAUTION!!!
                #put this code in the end!!! in order to insure the order of the text display is correct!!!!
                self.played = False

    def send(self):
        while self.running:
            if self.gameOver:
                request = json.dumps({'r_type': Protocols.Request.COMMAND, 'data': 'quit'})
                self.client.send(request.encode('utf-8'))
                self.gameOver = False
                self.played = True
            if self.played:
                continue
            message = ''
            while message not in ['R', 'P', 'S']:
                if self.running == False:
                    return
                print('-'*50)
                message = input('Play Rock, Paper, Scissors [R/P/S]: ')
                if len(message) > 0 and message[0] == '/':
                    break
            if not self.running:
                return
            if len(message) > 0 and message[0] == '/':
                message = message.removeprefix('/')
                request = json.dumps({'r_type': Protocols.Request.COMMAND, 'data': message})
                self.client.send(request.encode('utf-8'))
            else:
                request = json.dumps({'r_type': Protocols.Request.PLAY, 'data': message})
                self.client.send(request.encode('utf-8'))
                self.played = True
    
    def close(self):
        self.running = False

if __name__ == "__main__":
    client = Client()
    client.run()