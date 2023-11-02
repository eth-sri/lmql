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
    async def __call__(self, *args, **kwargs):
        """
        Resumes the resumable context with the given arguments.
        """
        pass

    @staticmethod
    def chain(*resumables):
        """
        Chains multiple resumables into a single resumable.

        The resumables are called in order, with the result of the 
        previous resumable being passed as argument to the next one.
        """
        if len(resumables) == 0:
            return None
        if len(resumables) == 1:
            return resumables[0]

        return ChainedResumable(resumables[0], resumables[1])

class ChainedResumable(resumable):
    def __init__(self, inner, outer):
        super().__init__()
        self.inner = inner
        self.outer = outer

    def copy(self):
        return ChainedResumable(self.inner.copy(), self.outer.copy())
    
    async def __call__(self, *args, **kwargs):
        inner_result = await self.inner(*args, **kwargs)
        outer_result = await self.outer(inner_result)
        return outer_result
    
class IdentityResumable(resumable):
    def __init__(self):
        super().__init__()

    def copy(self):
        return IdentityResumable()
    
    async def __call__(self, *args, **kwargs):
        return args[0]

identity = IdentityResumable()