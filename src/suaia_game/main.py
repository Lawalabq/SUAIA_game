import queue

from tracker import Tracker
from  game import play_game  



shared_buffer = queue.Queue()

tracker = Tracker(shared_buffer=shared_buffer)
game = play_game(shared_buffer=shared_buffer,tracker=tracker)

game.main()
tracker.start()






