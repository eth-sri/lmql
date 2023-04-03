from typing import List, Dict, Any

# check if langchain is available
try:
    from langchain.chains.base import Chain

    class LMQLChainMixIn(Chain):
        def _call(self, inputs: Dict[str, str]) -> Dict[str, str]:
            import asyncio

            if LMQLChainMixIn.loop is None:
                LMQLChainMixIn.loop = asyncio.new_event_loop()
            loop = LMQLChainMixIn.loop
            
            asyncio.set_event_loop(loop)

            argnames = self.args
            args = [inputs[argname] for argname in argnames]

            task = self.__acall__(*args)
            try:
                res = loop.run_until_complete(task)
            except:
                LMQLChainMixIn.loop = asyncio.get_event_loop()
                print(LMQLChainMixIn.loop)
                res = loop.run_in_executor(None, task)
            res = [{k:v for k,v in r.variables.items()} for r in res]

            if len(res) == 1:
                res = res[0]

            return res

    LMQLChainMixIn.loop = None
except ImportError as e:
    class LMQLChainMixIn:
        pass