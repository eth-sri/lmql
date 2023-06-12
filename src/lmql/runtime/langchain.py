from typing import List, Dict, Any

global lmql_chain_loop
lmql_chain_loop = None
from .loop import call_sync

def chain(lmql_query_function, output_keys=None):
    from langchain.chains.base import Chain
    class LMQLChain(Chain):
        custom_output_keys: List[str]

        def __init__(self):
            super().__init__(custom_output_keys=output_keys or lmql_query_function.output_variables)

        @property
        def output_keys(self) -> List[str]:
            return self.custom_output_keys
        
        @property
        def input_keys(self) -> List[str]:
            return lmql_query_function.input_keys

        def _call(self, inputs: Dict[str, str]) -> Dict[str, str]:
            import asyncio
            res = call_sync(lmql_query_function, **inputs)
            
            assert type(res) is not asyncio.Future, "Failed to async call lmql query function"
            
            def convert_result(r):
                if hasattr(r, "variables"):
                    return {k:v for k,v in r.variables.items()}
                return r

            res = [convert_result(r) for r in res]

            if len(res) == 1:
                res = res[0]

            return res

    return LMQLChain()

