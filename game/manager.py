from typing import Dict, Optional
from game.models import Game, Player

class GameManager:
    def __init__(self):
        self.games: Dict[int, Game] = {}

    def get_game(self, chat_id: int) -> Optional[Game]:
        return self.games.get(chat_id)

    def create_game(self, chat_id: int) -> Game:
        if chat_id in self.games:
            # Cancel timer task if active
            if self.games[chat_id].timer_task:
                self.games[chat_id].timer_task.cancel()
        self.games[chat_id] = Game(chat_id)
        return self.games[chat_id]

    def remove_game(self, chat_id: int):
        if chat_id in self.games:
            game = self.games[chat_id]
            if game.timer_task:
                game.timer_task.cancel()
            del self.games[chat_id]

    def get_game_by_player(self, user_id: int) -> Optional[Game]:
        for game in self.games.values():
            if user_id in game.players:
                return game
        return None

# Global instance of GameManager
game_manager = GameManager()
