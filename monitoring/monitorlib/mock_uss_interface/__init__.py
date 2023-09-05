from abc import ABC
from typing import List
from flask import Request, Response


class ResponseHook(ABC):
    def after_res(self, response: Response, function):
        raise NotImplementedError("ResponseHook subclass did not implement after_res")


res_hooks: List[ResponseHook] = []


def call_res_hooks(req: Request, res: Response):
    for hook in res_hooks:
        hook.after_res(res, res)
