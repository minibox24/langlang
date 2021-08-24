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
    BASH = ("bash", "sh")
    C = ("c", "c")
    CPP = ("cpp", "cc")
    CSHARP = ("csharp", "cs")
    GO = ("go", "go")
    JAVA = ("java", "java")
    JAVASCRIPT = ("javascript", "js")
    KOTLIN = ("kotlin", "kt")
    PYTHON = ("python", "py")
    TEXT = ("text", "txt")
    TYPESCRIPT = ("typescript", "ts")

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
    def __init__(self, container, command):
        Thread.__init__(self, daemon=True)

        self.container = container
        self.command = command
        self.result = None
        self.exited = False

    def run(self):
        self.result = self.container.exec_run(self.command)
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
        docker_copy_code(container, f"Main.{ext}", code)

        thread = ExecThread(container, "/bin/sh /compile.sh")
        thread.start()
        compile_raw_result, exited = thread.join(TIMEOUT)

        print(f"[COMPILE] {compile_raw_result}\n\n")

        thread = ExecThread(container, "/bin/sh /run.sh")
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

    with tarfile.open(fileobj=stream, mode="w|", encoding="utf8") as tar:
        encoded = code.encode("utf8")
        f = BytesIO(encoded)
        f.name = filename

        info = tarfile.TarInfo(name=filename)
        info.mtime = time.time()
        info.size = len(encoded)

        tar.addfile(info, f)

    container.put_archive("/", stream.getvalue())


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
            print(f"BUILDING {lang}")
            client.images.build(path=f"./languages/{lang}", tag=f"langlang:{lang}")
            print(f"BUILT {lang}")
