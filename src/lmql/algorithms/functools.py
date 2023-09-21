import asyncio
import sys
from .cache import apply

async def map(q, items, chunksize=None, progress=False, parameter=None, **kwargs):
    chunks = []
    if chunksize is None:
        chunksize = len(items)
    for i in range(0, len(items), chunksize):
        chunks.append(items[i:i+chunksize])
    
    total_results = []

    if progress:
        import tqdm
        chunks = tqdm.tqdm(chunks, file=sys.stdout)

    for chunk in chunks:
        results = await asyncio.gather(*[apply(q, x, **kwargs) for x in chunk])
        total_results += results

    return total_results

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