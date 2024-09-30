class Protocols:
    class Request:
        COMMAND = 'request.command'
        MESSAGE = 'request.message'
        PLAY = 'request.play'

    class Response:
        COMMAND = 'response.command'
        MESSAGE = 'response.message'
        GAMESTATE = 'response.gamestates'