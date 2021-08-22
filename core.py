from subprocess import (
    Popen,
    check_output,
    PIPE,
    STDOUT,
    CalledProcessError,
    TimeoutExpired,
)
from threading import Thread
from io import BytesIO
from enum import Enum
from config import *
import tarfile
import time
import os


class Languages(Enum):
    PYTHON = ("python", "py")
    CPP = ("cpp", "cpp")
    KOTLIN = ("kotlin", "kt")
    JAVASCRIPT = ("javascript", "js")
    TYPESCRIPT = ("typescript", "ts")
    GO = ("go", "go")
    BASH = ("bash", "sh")

    @classmethod
    def find(cls, name):
        for item in cls:
            if item.value[0] == name:
                return item
        raise ValueError


class Status(Enum):
    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"
    MEMORY_OVERFLOW = "memory_overflow"


class DeleteThread(Thread):
    def __init__(self, container):
        Thread.__init__(self)
        self.container = container

    def run(self):
        self.container.remove(force=True)


class ExecThread(Thread):
    def __init__(self, container):
        Thread.__init__(self, daemon=True)

        self.container = container
        self.result = None
        self.exited = False

    def run(self):
        self.result = self.container.exec_run("/bin/sh /run.sh")
        self.exited = True

    def join(self, *args):
        Thread.join(self, *args)
        return self.result, self.exited


def run(client, code, language):
    name, ext = language.value

    status = Status.OK
    result = None

    container = client.containers.run(
        f"langlang:{name}",
        "/bin/sh",
        detach=True,
        tty=True,
        mem_limit=f"{MEMORY}m",
        nano_cpus=int(CPUS * 1e9),
        network_disabled=True,
    )

    try:
        docker_copy_code(container, f"script.{ext}", code)

        thread = ExecThread(container)
        thread.start()
        raw_result, exited = thread.join(TIMEOUT)

        if not exited:
            status = Status.TIMEOUT
        else:
            exit_code, result = raw_result
            result = result.decode().rstrip()

            if exit_code == 137:
                status = Status.MEMORY_OVERFLOW
            elif exit_code != 0:
                status = Status.ERROR
    finally:
        DeleteThread(container).start()

    return status, result


def docker_copy_code(container, filename, code):
    stream = BytesIO()

    with tarfile.open(fileobj=stream, mode="w|") as tar:
        f = BytesIO(code.encode())
        f.name = filename

        info = tarfile.TarInfo(name=filename)
        info.mtime = time.time()
        info.size = len(code)

        tar.addfile(info, f)

    container.put_archive(path="/", data=stream.getvalue())


def get_images(client):
    return list(
        map(lambda i: i.tags[0].split(":")[1], client.images.list(name="langlang"))
    )


def setup(client):
    if not os.path.isdir("./temp"):
        print(f"create temp directory")
        os.mkdir("./temp")

    images = get_images(client)

    for lang in os.listdir("./languages"):
        if lang not in images:
            print(f"{lang} not found, building...", end=" ")
            client.images.build(path=f"./languages/{lang}", tag=f"langlang:{lang}")
            print("end")
