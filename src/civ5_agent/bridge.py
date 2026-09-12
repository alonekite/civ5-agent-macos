from abc import ABC, abstractmethod
from .models import Command, CommandResult, GameState

class Bridge(ABC):
    @abstractmethod
    def read_state(self) -> GameState: ...
    @abstractmethod
    def submit(self, command: Command) -> None: ...
    @abstractmethod
    def get_result(self, command_id: str) -> CommandResult | None: ...
