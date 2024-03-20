
class SystemEvents:
    
    def __init__(self, new_event_callback=None) -> None:
        self.event_list = []
        self.new_event_callback = new_event_callback

    def append(self, event):
        self.event_list.append(event)
        if self.new_event_callback:
            self.new_event_callback(event)

    def clear_events(self):
        self.event_list.clear()

    def get_events(self):
        return self.event_list
