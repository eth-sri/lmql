from .tracer import Tracer, NullTracer
from lmql.version import version, build_on, commit
import json
import time

class InferenceCertificate:
    """
    An LMQL inference certificate is a data structure that contains information
    about the exact execution of an LMQL query. It is used to trace and document
    the exact model calls that have lead to a certain result.
    """
    def __init__(self, tracer):
        self.tracer = tracer

        # extra 'event' processors to make the certificate more readable
        self.event_processors = [
            flatten_streamed_chat_responses,
            flatten_streamed_openai_completion,
            fold_logit_bias
        ]

    def asdict(self, child=False):
        if type(self.tracer) is NullTracer:
            return {
                "type": "lmql.InferenceCertificate",
                "warning": "Untraced query. Make sure to use lmql.traced() or certificate=True to trace your queries."
            }

        return {
            "name": self.tracer.name,
            **({
                "type": "lmql.InferenceCertificate",
                "lmql.version": f"{version} (build on {build_on}, commit {commit})",
                "time": time.strftime("%Y-%m-%d %H:%M:%S %z")
               } if not child else {}),
            **({"events": self.process_events()} if len(self.tracer.events) > 0 else {}),
            **({"children": [certificate(c).asdict(child=True) for c in self.tracer.children]} if len(self.tracer.children) > 0 else {}),
            **({"metrics": self.tracer.metrics} if len(self.tracer.metrics) > 0 else {})
        }

    def __str__(self) -> str:
        return json.dumps(self.asdict(), indent=4)
    
    def process_events(self):
        events = self.tracer.events
        for p in self.event_processors:
            events = [p(e) for e in events]
        return events

    def __repr__(self) -> str:
        return str(self)

def certificate(tracer: Tracer, empty_on_null=False):
    """
    Generates an LMQL inference certificate from the given tracer.

    This includes information on the exact model calls that have lead to a
    certain result.
    """
    if type(tracer) is NullTracer:
        if empty_on_null: 
            return InferenceCertificate(NullTracer())
        return None
    return InferenceCertificate(tracer)

def flatten_streamed_chat_responses(event):
    def flatten_chat(chat):
        # make sure all messages only contain 'content' and 'role' as keys
        if not all([set(m.keys()).issubset(["content", "role"]) for m in chat]):
            print(chat)
            return chat
        # flatten the chat
        role = ""
        text = ""
        for m in chat:
            # if the role changes throughout, do not transform
            if "role" in m.keys() and role != "":
                return chat
            role = m["role"] if "role" in m else role
            text += m["content"]
        return [{
            "role": role,
            "content": text
        }]
    
    name = event.get("name")
    if name == "openai.ChatCompletion":
        for k in event.get("data").keys():
            if k.startswith("result["):
                event["data"][k] = flatten_chat(event["data"][k])

    return event

def flatten_streamed_openai_completion(event):
    def flatten(text):
        # if not all are strings, this is an unexpected format
        if not all([type(t) is str for t in text]):
            return text
        # flatten the text
        return "".join(text)

    name = event.get("name")
    if name == "openai.Completion":
        for k in event.get("data").keys():
            if k.startswith("result["):
                event["data"][k] = flatten(event["data"][k])
    
    return event

def fold_logit_bias(event):
    name = event.get("name")
    if name in ["openai.Completion", "openai.ChatCompletion"]:
        # check for data.kwargs.logit_bias
        if "kwargs" in event.get("data").keys() and "logit_bias" in event.get("data").get("kwargs").keys():
            event["data"]["kwargs"]["logit_bias"] = "{" + ", ".join([f"{k}: {v}" for k, v in event["data"]["kwargs"]["logit_bias"].items()]) + "}"
    
    return event