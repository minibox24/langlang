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
    CPP = ("cpp", "cpp")
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
    COMPILE_ERROR = "compile_error"


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


def run(client, code, language, input_):
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
        if input_:
            files = [
                make_tarinfo(f"Main.{ext}", code),
                make_tarinfo("input", input_),
                make_tarinfo("runInput.sh", "/bin/sh /run.sh < /input"),
            ]

            container.put_archive("/", make_tarfile(*files))
        else:
            docker_copy_code(container, f"Main.{ext}", code)

        done_compile = False

        thread = ExecThread(container, "/bin/sh /compile.sh")
        thread.start()
        compile_raw_result, exited = thread.join(TIMEOUT)

        if not exited:
            status = Status.COMPILE_ERROR
        else:
            compile_exit_code, result = compile_raw_result
            compile_result = result.decode().rstrip()

            if compile_exit_code != 0:
                status = Status.COMPILE_ERROR
                result = compile_result
            else:
                done_compile = True

        if done_compile:
            thread = ExecThread(
                container, f"/bin/sh /{'runInput' if input_ else 'run'}.sh"
            )
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


def make_tarinfo(filename, source):
    encoded = source.encode()
    f = BytesIO(encoded)
    f.name = filename

    info = tarfile.TarInfo(name=filename)
    info.mtime = time.time()
    info.size = len(encoded)

    return info, f


def make_tarfile(*tarinfo):
    stream = BytesIO()

    with tarfile.open(fileobj=stream, mode="w|", encoding="utf8") as tar:
        for item in tarinfo:
            tar.addfile(*item)

    return stream.getvalue()


def docker_copy_code(container, filename, code):
    container.put_archive("/", make_tarfile(make_tarinfo(filename, code)))


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
