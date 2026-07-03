from typing import Dict, List, Optional
import asyncio

class Player:
    def __init__(self, user_id: int, name: str, username: Optional[str] = None):
        self.user_id = user_id
        self.name = name
        self.username = username
        self.role: Optional[str] = None  # Mafia, Don, Civilian, Detective, Doctor, Bodyguard, Courtesan, Maniac
        self.is_alive = True
        self.is_blocked = False
        self.is_healed = False
        self.is_guarded = False
        self.role_booster: Optional[str] = None # User can use booster card

    def reset_night_status(self):
        self.is_blocked = False
        self.is_healed = False
        self.is_guarded = False

class Game:
    def __init__(self, chat_id: int):
        self.chat_id = chat_id
        self.players: Dict[int, Player] = {}
        self.phase = "lobby"  # lobby, night, day, voting, ended
        self.timer_task: Optional[asyncio.Task] = None
        self.votes: Dict[int, int] = {}  # voter_id -> target_id
        # Tungi harakatlar: role -> list of targets or single target
        # E.g., mafia -> dict of voter -> target
        self.night_actions = {
            "mafia": {},       # voter_id -> target_id (Mafia vote)
            "don": None,       # target_id (Don check)
            "detective_check": None, # Detective check target
            "detective_shoot": None, # Detective shoot target
            "doctor": None,    # target_id (Doctor heal)
            "bodyguard": None, # target_id (Bodyguard guard)
            "courtesan": None, # target_id (Courtesan block)
            "maniac": None     # target_id (Maniac kill)
        }
        self.event: Optional[dict] = None  # Current day event
        self.messages_to_delete: List[int] = []
        self.vote_message_id: Optional[int] = None
        self.lobby_message_id: Optional[int] = None
        
        # Last targets to prevent doctor/bodyguard from healing/protecting the same person twice in a row
        self.last_doctor_target: Optional[int] = None
        self.last_bodyguard_target: Optional[int] = None
        
        # Last words states
        self.waiting_last_words: Dict[int, bool] = {}
        self.last_words: Dict[int, str] = {}

    def get_alive_players(self) -> List[Player]:
        return [p for p in self.players.values() if p.is_alive]

    def get_players_by_role(self, role: str, alive_only: bool = True) -> List[Player]:
        return [p for p in self.players.values() if p.role == role and (not alive_only or p.is_alive)]
