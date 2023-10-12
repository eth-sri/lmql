from typing import List, Union
from contextvars import ContextVar
from typing import Any
import warnings
import inspect
import json
import dataclasses

REDACT_KEYS = ["Authorization"]

def add_extra_redact_keys(keys: Union[str, List[str]]):
    """
    Adds a new globally-enforced dictionary keys to redact from all traced 
    dictionaries (applies recursively). The corresponding values will be
    replaced by "<removed>".
    """
    if type(keys) is str:
        keys = [keys]

    global REDACT_KEYS
    REDACT_KEYS += keys

def remove_none_keys(dict_data):
    if type(dict_data) is dict:
        return {k: remove_none_keys(v) for k, v in dict_data.items() if v is not None}
    elif type(dict_data) is list:
        return [remove_none_keys(v) for v in dict_data]
    else:
        return dict_data

def redact_data(dict_data, redact):
    keys_to_redact = (redact if type(redact) is list else []) + REDACT_KEYS

    if type(dict_data) is dict:
        return {k: redact_data(v, redact) if k not in REDACT_KEYS else "<removed>" for k, v in dict_data.items()}
    elif type(dict_data) is list:
        return [redact_data(v, redact) for v in dict_data]
    else:
        s = str(dict_data)
        for k in keys_to_redact:
            if k in s:
                return "<removed>"
        return dict_data

class Tracer:
    """
    An LMQL tracer is a context manager that can be used to trace and log 
    the execution of an LMQL query.
    """
    def __init__(self, name: str, parent = None):
        """
        Creates a new LMQL tracer.

        :param parent: The parent tracer, if any. All log messages will be
        forwarded to the parent tracer as well.
        """
        self.name = name
        self.parent = parent

        self.events = []
        self.metrics = {}
        self.children = []

        self.active = True

    def event(self, name, data, redact=None, skip_none=False):
        try:
            # check for dataclasses
            if dataclasses.is_dataclass(data):
                data = dataclasses.asdict(data)
            # check for list of dataclasses
            elif type(data) is list and len(data) > 0 and dataclasses.is_dataclass(data[0]):
                data = [dataclasses.asdict(d) for d in data]
            
            # process event data
            if skip_none:
                data = remove_none_keys(data)
            data = redact_data(data, redact)
            
            s = json.dumps(data)
            data = json.loads(s)
        except:
            warnings.warn("Tracer: cannot log or trace non-serializable data: {}".format(data), RuntimeWarning)
            return
        
        self.events.append({
            "name": name,
            "data": data
        })
        # updateable event handle
        return Event(self.events[-1])

    def add(self, metric_name, n=1):
        """
        Adds a value to the given metric.
        """
        if self.parent is not None:
            self.parent.add(metric_name, n)

        # split by dot as a hierarchy
        parts = metric_name.split(".")
        # make sure path exists
        current = self.metrics
        for i in range(len(parts) - 1):
            current = current.setdefault(parts[i], {})
        # add value
        current[parts[-1]] = current.get(parts[-1], 0) + n

    def add_child_tracer(self, tracer):
        self.children.append(tracer)
        tracer.parent = self

    def __str__(self):
        children_str = ""
        if len(self.children) > 0:
            children_str = " children=[\n{}\n".format("\n".join([" - " + str(c) for c in self.children]))

        return "<lmql.Tracer '{}' events={} metrics={}{}]>".format(self.name, len(self.events), len(self.metrics), children_str)

class Event:
    def __init__(self, entry):
        self.entry = entry

    def update(self, data):
        self.entry["data"] = {**self.entry["data"], **data}

    def add(self, key, data):
        default_value = "" if type(data) is str else []
        self.entry["data"][key] = self.entry["data"].get(key, default_value) + data

class NullTracer:
    def __init__(self, name, *args, parent=None, **kwargs):
        # keep name, for the case we switch to a real tracer
        self.name = name
        self.parent = parent

        self.active = False
    
    def __getattribute__(self, __name: str) -> Any:
        if __name in ["name", "__dict__", "parent", "active", "__str__", "__repr__"]:
            return super().__getattribute__(__name)
        return self
    
    def __call__(self, *args, **kwargs):
        # do nothing
        return self
    
    def __str__(self):
        return "<lmql.NullTracer '{}'>".format(self.name)
    
    def __repr__(self):
        return str(self)

# context var for the current tracer
_tracer = ContextVar("logger")
_tracer.set([])

def _ensure_tracer():
    try:
        _tracer.get()
    except LookupError:
        _tracer.set([])

def has_tracer():
    """
    Returns True if a tracer is currently active in this context.
    """
    _ensure_tracer()
    return len(_tracer.get()) > 0

def active_tracer() -> Tracer:
    """
    Returns the LMQL tracer instance that is currently active in this context.

    This value is set by context in the LMQL interpreter run() function, to enable 
    different tracers in sub-queries.
    """
    _ensure_tracer()
    if len(_tracer.get()) == 0:
        warnings.warn("An LMQL tracer was requested in a context without active tracer. This indicates that some internal LLM calls may not be traced correctly.")
        return NullTracer("null")
    return _tracer.get()[-1]

def set_tracer(tracer):
    _ensure_tracer()
    _tracer.set(_tracer.get() + [tracer])

def pop_tracer():
    _ensure_tracer()
    _tracer.set(_tracer.get()[:-1])

class ContextTracer:
    def __init__(self, tracer):
        self.tracer = tracer

    def __enter__(self):
        _ensure_tracer
        current = _tracer.get()[-1] if len(_tracer.get()) > 0 else None
        if current is not None:
            if self.tracer.parent is not None:
                import traceback
                warnings.warn("An LMQL child tracer has been activated with an existing parent tracer. The hierarchical structure of the resulting trace may be incorrect.")
                traceback.print_stack()
            else:
                current.add_child_tracer(self.tracer)
        set_tracer(self.tracer)
        return self.tracer
    
    def __exit__(self, exc_type, exc_value, traceback):
        pop_tracer()
        return False

def enable_tracing():
    """
    Enables tracing of all LMQL queries executed in the current 
    context (descendant queries created in the current context).
    """
    _ensure_tracer()
    tracers = _tracer.get()
    assert len(tracers) > 0, "No tracer set in this context"
    
    # if the last tracer is a null tracer, replace it with a real one
    if type(tracers[-1]) is NullTracer:
        tracers[-1] = Tracer(tracers[-1].name, tracers[-1].parent)

def trace(name):
    """
    Decorator @trace(<name>) that creates and applies a new LMQL 
    tracer to the decorated function.
    """
    def decorator(fct):
        if inspect.iscoroutinefunction(fct):
            async def wrapper(*args, **kwargs):
                if not has_tracer():
                    tracer = NullTracer(name)
                else:
                    tracer = Tracer(name)

                with ContextTracer(tracer):
                    return await fct(*args, **kwargs)
        else:
            def wrapper(*args, **kwargs):
                if not has_tracer():
                    tracer = NullTracer(name)
                else:
                    tracer = Tracer(name)
                
                with ContextTracer(tracer):
                    return fct(*args, **kwargs)
        return wrapper
    return decorator

def traced(name):
    """
    Context manager to execute an LMQL workload in a traced manner.

    Example:

    with lmql.traced("my workload"):
        await query1()
        await query2()
    
    """
    tracer = Tracer(name)
    return ContextTracer(tracer)