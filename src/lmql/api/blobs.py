from weakref import WeakValueDictionary
import re

blob_store = WeakValueDictionary()

class Blob:
    """
    Represents multi-modal data as part of an LMQL prompt.
    """
    def __init__(self, data):
        self.data = data
        self.id = str(hash(data))
        
        blob_store[self.id] = self

    @staticmethod
    def resolve(id):
        return blob_store.get(id)
    
    def __str__(self):
        return f"<Blob {[str(self.data)]}>"
    
    def __repr__(self):
        return str(self)

    @staticmethod
    def decode(text):
        print("decode", [text])
        pattern = r"<lmql:media([^>]*)\>"
        # split text by pattern matches, and replace each match with the resolved blob
        parts = re.split(pattern, text)
        for i in range(1, len(parts), 2):
            id = parts[i].split("id='")[1].split("'")[0]
            print([id])
            parts[i] = Blob.resolve(id)
        return text