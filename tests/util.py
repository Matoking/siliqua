import socket
import time

from contextlib import closing


def wait_for(condition, timeout=1):
    start = time.time()

    while not condition():
        if time.time() > (start + timeout):
            raise TimeoutError()

        time.sleep(0.1)


def hook(orig_func, after=None, before=None):
    def wrapper(*args, **kwargs):
        if before:
            before._wrapped_method = orig_func
            before(*args, **kwargs)
        result = orig_func(*args, **kwargs)

        if after:
            after._wrapped_method = orig_func
            after(*args, **kwargs)

        return result

    return wrapper


def find_free_port():
    # https://stackoverflow.com/a/45690594
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(('', 0))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        port = sock.getsockname()[1]
        return port


def async_hook(func, orig_func):
    async def wrapper(*args, **kwargs):
        func._wrapped_method = orig_func
        result = await orig_func(*args, **kwargs)
        await func(*args, **kwargs)
        return result

    return wrapper


def to_hex(num, digits):
    s = hex(num)[2:]

    if len(s) < digits:
        s = "0"*(digits-len(s)) + s

    return s


class PartialMatch:
    def __init__(self, substr):
        self.substr = substr


class HTTPReplay:
    def __init__(self, req, resp, stage=0, block_to_confirm=None):
        self.req = req
        self.resp = resp
        self.stage = stage
        self.block_to_confirm = block_to_confirm

    def match(self, request):
        if self.req.keys() != request.keys():
            return False

        for key, val in self.req.items():
            if isinstance(val, PartialMatch):
                if val.substr not in request[key]:
                    return False
            elif request[key] != val:
                return False

        return True


class WebSocketReplay:
    def __init__(self, topic, options, response):
        self.topic = topic
        self.options = options
        self.response = response
