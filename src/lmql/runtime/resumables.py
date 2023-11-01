from abc import ABC, abstractmethod

class resumable(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def copy(self):
        """
        Returns a copy of this resumable object.

        Copied resumables allow to re-enter a resumable context at 
        a later point in time, independent whether or not the original
        resumable context is still active.
        """
        pass

    @abstractmethod
    def __call__(self, *args, **kwargs):
        """
        Resumes the resumable context with the given arguments.
        """
        pass