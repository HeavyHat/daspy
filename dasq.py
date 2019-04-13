from __future__ import annotations
import threading
import time
import requests
import json
from urllib.parse import urljoin
from contextlib import ContextDecorator
from typing import Optional, List, Dict
from dataclasses import dataclass, field
from collections import namedtuple
import color

DEFAULT_BACKEND_URL="http://localhost:27301/"
DEFAULT_PID = "DK5QPID"
DEFAULT_EFFECT = "SET_COLOR"
DEFAULT_COLOR = color.ALICEBLUE.hex_format()
DEFAULT_ZONE = "KEY_Q"
DEFAULT_CLIENT = "Python Script"
DEFAULT_NAME = ""
DEFAULT_MESSAGE = ""
headers = { "Content-type": "application/json"}


@dataclass
class Signal(object):
    backendUrl: str = field(default=DEFAULT_BACKEND_URL)
    zoneId : Union[str, List[str]] = field(default=DEFAULT_ZONE)
    color: Union[str, List[str]] = field(default=DEFAULT_COLOR)
    effect: str = field(default=DEFAULT_EFFECT)
    pid: str = field(default=DEFAULT_PID)
    clientName: str = field(default=DEFAULT_CLIENT)
    message: str = field(default=DEFAULT_MESSAGE)
    name: str = field(default=DEFAULT_NAME)
    subscribers: List[object]=field(default_factory=list)
    response: object = field(default_factory=dict)
       
    def for_zone(self, zoneId: str) -> Signal:
        self.zoneId = zoneId
        return self

    def with_color(self, color_obj: Union[str,color.RGB]) -> Signal:
        if isinstance(color_obj, color.RGB):
            self.color = color_obj.hex_format()
        else:
            self.color = color_obj
        return self

    def with_effect(self, effect: str) -> Signal:
        self.effect = effect
        return self

    def with_pid(self, pid: str) -> Signal:
        self.pid = pid
        return self

    def with_client_name(self, client_name:str) -> Signal:
        self.client_name = client_name
        return self

    def with_message(self, message:str) -> Signal:
        self.message = message
        return self

    def with_name(self, name:str) -> Signal:
        self.name = name
        return self

    def as_dict(self) -> Dict[str,str]:
        return dict(zip(dir(self)))

    def finalize(self, endpoint: Optional[str] = "/api/1.0/signals", publish: Optional[bool] = True) -> Union[Dict[str, str], dict]:
        returns = []
        if isinstance(self.zoneId, list):
            for i, zoneId in enumerate(self.zoneId):
                signal = deepcopy(self)
                signal.zoneId = zoneId
                if isinstance(self.color, list):
                    signal.color = self.color[i]
                returns += signal.finalize(endpoint,nublish)
        else:
            field_names = {"zoneId", "color", "effect", "pid", "clientName", "message", "name"}
            keys = [field for field in dir(self) if field in field_names]
            values = [getattr(self,key) for key in keys]
            if publish:
                returns += requests.post(urljoin(self.backendUrl,endpoint), data=json.dumps(dict(zip(keys, values))), headers=headers)
            returns += json.dumps(dict(zip(keys, values)))
        return returns

    def delete(self):
        return requests.delete(urljoin(self.backendUrl,f"/api/1.0/signals/pid/{self.pid}/zoneId/{self.zoneId}"), headers=headers)            

def delete_after(seconds:int):
    return lambda x: threading.Timer(seconds, x.delete).start()

class QSession(ContextDecorator):

    def __init__(self, delete_on_exit=False, for_each_signal=lambda x: x,**kwargs):
        self.defaults = kwargs
        self.for_each_signal = for_each_signal
        self.delete_on_exit = delete_on_exit
        self.signals = []

    def signal(self) -> Signal:
        signal = Signal(**self.defaults)
        self.for_each_signal(signal)
        self.signals.append(signal)
        return signal

    def __enter__(self) -> QSession:
        return self

    def __exit__(self, *exc) -> bool:
        for signal in self.signals:
            if self.delete_on_exit:
                signal.delete()
        return False

    def subscription(self, data: Dict[str,str]) -> None:
        self.signals[data["request"]] = data["response"]


class SignalStream(object):

    def __init__(self, delay: Optional[int] = 0 , session: Optional[QSession] = QSession(delete_on_exit=False)):
        self.session = session
        self.delay = delay

    def __lshift__(self, string:str) -> SignalStream:
        string = string.upper()
        for character in string:
            key = f"KEY_{character}"
            time.sleep(self.delay)
            self.session.signal() \
                    .for_zone(key) \
                    .finalize()
        return self
