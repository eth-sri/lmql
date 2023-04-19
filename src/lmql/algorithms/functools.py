import asyncio
import sys
from .cache import apply

async def map(q, items):
    return await asyncio.gather(*[apply(q, x) for x in items])

async def reduce(f, items, initial=None):
    if initial is None:
        acc = items[0]
        items = items[1:]
    else:
        acc = initial
    
    for item in items:
        acc = await apply(f, acc, item)
    
    return acc

async def chain(*queries):
    pass

async def azip(*args):
    pass

async def sorted(*args, cmp_query, **kwargs):
    pass