from enum import Enum

class EventType(Enum):

    USER_MESSAGE = 1
    API_CALL = 2
    API_RESULT = 3
    SYSTEM_MESSAGE = 4
    VOICE_EVENT_LISTENING = 5
    VOICE_EVENT_FINISHED = 6

class EventMessages:
    
    def __init__(self) -> None:
        self.event_list = []
        self.event_callbacks = []

    def add_callback(self, callback_function):
        self.event_callbacks.append(callback_function)

    def message(self, event_type:EventType, event_message:str):
        self.event_list.append((event_type, event_message))
        for fn in self.event_callbacks:
            fn((event_type, event_message))

    def pop_all_events(self):
        # n is current list size
        n = len(self.event_list)
        # get first n elements
        pop = self.event_list[:n] 
        # remove first n elements and leave the rest (in case new elements where added)
        self.event_list = self.event_list[n:]
        # return removed elements
        return pop

event_log = EventMessages()