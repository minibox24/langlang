from subprocess import (
    Popen,
    check_output,
    PIPE,
    STDOUT,
    CalledProcessError,
    TimeoutExpired,
)
from threading import Thread
from enum import Enum
from config import *
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
    OK = ("ok",)
    ERROR = "error"
    TIMEOUT = "timeout"
    MEMORY_OVERFLOW = "memory_overflow"


class DeleteThread(Thread):
    def __init__(self, cid):
        Thread.__init__(self)
        self.cid = cid

    def run(self):
        Popen(f"docker stop {self.cid}", stdout=PIPE, shell=True).communicate()
        Popen(f"docker rm {self.cid}", stdout=PIPE, shell=True).communicate()


def run(code, language):
    name, ext = language.value

    status = Status.OK
    result = None
    cid = (
        (
            check_output(
                f"docker run -dt -m {MEMORY}m --cpus {CPUS} --net=none langlang:{name} /bin/sh",
                shell=True,
            )
        )
        .decode()
        .rstrip()
    )

    try:
        with open(f"./temp/{cid}", "w", encoding="utf8") as f:
            f.write(code)

        check_output(f"docker cp ./temp/{cid} {cid}:script.{ext}", shell=True)

        try:
            raw_output = check_output(
                f"docker exec {cid} /bin/sh /run.sh",
                stderr=STDOUT,
                shell=True,
                timeout=TIMEOUT,
            )
            result = raw_output.decode().rstrip()
        except CalledProcessError as e:
            if e.returncode == 137:
                status = Status.MEMORY_OVERFLOW
            else:
                result = e.output.decode().rstrip()
                status = Status.ERROR
        except TimeoutExpired:
            status = Status.TIMEOUT
    finally:
        if os.path.isfile(f"./temp/{cid}"):
            os.remove(f"./temp/{cid}")

        DeleteThread(cid).start()

    return status, result


def setup():
    if not os.path.isdir("./temp"):
        print(f"create temp directory")
        os.mkdir("./temp")

    images = (
        check_output('docker images langlang --format "{{.Tag}}"', shell=True)
        .decode()
        .rstrip()
        .split("\n")
    )

    for lang in os.listdir("./languages"):
        if lang not in images:
            print(f"{lang} not found, building...")
            check_output(
                f"docker build -t langlang:{lang} ./languages/{lang}", shell=True
            )
            print(f"{lang} built")
