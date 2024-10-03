from protocols import Protocols
import json
import socket

#handles the data the the server sends, recieves
#currently the room class can only have 2 clients
class Room:

    response_queue:list = []
    clients:dict[socket.socket, int] = {}
    plays:dict[int, str] = {}
    scores:dict[int, int] = {}

    MIN_CLIENT_NUM = 2
    MAX_CLIENT_NUM = 4
    BEST_OF = 3

    def __init__(self, clients:dict[socket.socket, int]) -> None:
        self.clients = clients
        for clientID in clients.values():
            self.scores[clientID] = 0
        print(self.scores)

    def handle_data(self, sender:socket.socket, json_data:dict) -> None:
        sender_id = self.clients.get(sender, -1)
        r_type = json_data['r_type']
        data = json_data['data']
        
        if r_type == Protocols.Request.COMMAND:
            response:bytes = json.dumps({'r_type': Protocols.Response.COMMAND, 'data': data}).encode('utf-8')
            reciever = [sender]
            self.response_queue.append((response, reciever))

        if r_type == Protocols.Request.MESSAGE:
            data = f'<ClientID: {sender_id}> {data}'
            response:bytes = json.dumps({'r_type': Protocols.Response.MESSAGE, 'data': data}).encode('utf-8')
            reciever:list = self.clients.keys()
            reciever.remove(sender)
            self.response_queue.append((response, reciever))

        if r_type == Protocols.Request.PLAY:
            self.plays[sender_id] = data
            #if all the clients have played a move
            if len(self.plays) == len(self.clients):
                winners = self.detmerine_winners()
                final_winner = -1
                #add scores to all the winners
                for winner in winners:
                    if winner == -1:
                        break
                    #if it is a draw
                    self.scores[winner] += 1
                    if self.scores[winner] >= self.BEST_OF:
                        final_winner = winner

                gamestate = {'plays': self.plays, 'winner_ids': winners, 'scores': self.scores, 'final_winner': final_winner}
                reciever:list = self.clients.keys()
                response:bytes = json.dumps({'r_type': Protocols.Response.GAMESTATE, 'data': gamestate}).encode('utf-8')
                self.plays = {}
                self.response_queue.append((response, reciever))
            else:
                response:bytes = json.dumps({'r_type': Protocols.Response.MESSAGE, 'data': 'Waiting for Opponent...'}).encode('utf-8')
                reciever = [sender]
                self.response_queue.append((response, reciever))

    def update_win_status(self):

        #FIX LATER!!!
        if len(self.clients) <= 1:
            return
        #if all the clients have played a move
        if len(self.plays) == len(self.clients):
            winners = self.detmerine_winners()

            #add scores to all the winners
            for winner in winners:
                if winner == -1:
                    break
                #if it is a draw
                self.scores[winner] += 1
            gamestate = {'plays': self.plays, 'winner_ids': winners, 'scores': self.scores}
            self.response:str = {'r_type': Protocols.Response.GAMESTATE, 'data': gamestate}
            self.reciever.extend(self.clients.keys())
            self.plays = {}

    def remove_client(self, conn:socket.socket):
        self.clients.pop(conn)
        self.update_win_status()
    
    "Change when more than 2 player is added!!!"
    def detmerine_winners(self) -> list:
        winners = []
        different_plays = set(self.plays.values())
        #if there is 1 or 3 hands played then it is a draw -> -1
        if len(different_plays) == 1 or len(different_plays) == 3:
            return [-1]
        hand1 = different_plays.pop()
        hand2 = different_plays.pop()
        winning_hand = self.detmerine_winning_hand(hand1, hand2)
        for id in self.plays.keys():
            if self.plays[id] == winning_hand:
                winners.append(id)
        return winners
        
    "Change when more than 2 player is added!!!"
    def detmerine_winning_hand(self, hand1, hand2) -> str:
        #key beats value
        win_table = {'R': 'S', 'S': 'P', 'P': 'R'}
        if win_table[hand1] == hand2:
            return hand1
        if win_table[hand2] == hand1:
            return hand2
        return None
        