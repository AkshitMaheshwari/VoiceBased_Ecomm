from collections import deque

class ConversationMemory:
    def __init__(self, max_length=10):
        self.buffer = deque(maxlen=max_length)

    def add_user(self, text):
        self.buffer.append({"role": "user", "content": text})
    
    def add_ai(self, text):
        self.buffer.append({"role": "ai", "content": text})

    def context(self):
        # Fixed: accessing dict correctly
        return "\n".join([f"{msg['role']}: {msg['content']}" for msg in self.buffer])