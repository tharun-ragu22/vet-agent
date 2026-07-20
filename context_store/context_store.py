from dataclasses import dataclass

@dataclass
class ConversationTurn:
    role: str
    content: str

class ContextStore:
    _store : dict[str, list[ConversationTurn]]= {}
    def get_context(self, call_sid : str) -> list[ConversationTurn]:
        """Gets the context of a conversation"""
        return self._store.get(call_sid, [])
    def add_message(self, call_sid: str, role: str, content: str) -> None:
        if call_sid not in self._store:
            self._store[call_sid] = []
        
        self._store[call_sid].append(
            ConversationTurn(
                role=role,
                content=content
            )
        )