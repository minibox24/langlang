from threading import Thread
from io import BytesIO
from enum import Enum
from config import *
import asyncio
import tarfile
import time
import os


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


async def get_images(client):
    images = await asyncio.to_thread(client.images.list, name="langlang")
    return list(map(lambda i: i.tags[0].split(":")[1], images))


async def setup(client):
    if not os.path.isdir("./temp"):
        print(f"create temp directory")
        await asyncio.to_thread(os.mkdir, "./temp")

    images = await get_images(client)

    async def build(lang):
        print(f"BUILDING {lang}")
        await asyncio.to_thread(
            client.images.build, path=f"./languages/{lang}", tag=f"langlang:{lang}"
        )
        print(f"BUILT {lang}")

    await asyncio.gather(
        *[
            build(lang)
            for lang in filter(lambda l: l not in images, os.listdir("./languages"))
        ]
    )


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


class Runner:
    def __init__(self, client, language, code, inputs=[]):
        self.client = client
        self.language = language
        self.code = code
        self.inputs = inputs

        self.container = None

        self.compile_ok = False
        self.result = None
        self.status = Status.OK

    async def setup(self):
        lang, ext = self.language.value

        self.container = await asyncio.to_thread(
            self.client.containers.run,
            f"langlang:{lang}",
            "/bin/sh",
            detach=True,
            tty=True,
            mem_limit=f"{MEMORY}m",
            nano_cpus=int(CPUS * 1e9),
            network_disabled=True,
        )

        if self.inputs:
            files = [
                make_tarinfo(f"Main.{ext}", self.code),
                make_tarinfo(
                    "runInput.sh",
                    "for f in $(ls | grep input | sort -V); do /bin/sh run.sh < $f; done",
                ),
            ]

            for i, content in enumerate(self.inputs):
                files.append(make_tarinfo(f"input{i}", content))

            await asyncio.to_thread(
                self.container.put_archive, "/", make_tarfile(*files)
            )
        else:
            await asyncio.to_thread(
                self.container.put_archive,
                "/",
                make_tarfile(make_tarinfo(f"Main.{ext}", self.code)),
            )

    async def compile(self):
        try:
            exit_code, raw_result = await asyncio.wait_for(
                asyncio.to_thread(self.container.exec_run, "/bin/sh /compile.sh"),
                TIMEOUT,
            )
        except asyncio.TimeoutError:
            self.status = Status.COMPILE_ERROR
            return

        result = raw_result.decode().rstrip()

        if exit_code != 0:
            self.status = Status.COMPILE_ERROR
            self.result = result
            return

        self.compile_ok = True

    async def run(self):
        if not self.compile_ok:
            return

        try:
            exit_code, raw_result = await asyncio.wait_for(
                asyncio.to_thread(
                    self.container.exec_run,
                    f"/bin/sh /{'runInput' if self.inputs else 'run'}.sh",
                ),
                TIMEOUT,
            )
        except asyncio.TimeoutError:
            self.status = Status.TIMEOUT
            return

        self.result = raw_result.decode().rstrip()

        if exit_code == 137:
            self.status = Status.MEMORY_OVERFLOW
        elif exit_code != 0:
            self.status = Status.ERROR

    async def clear(self, background=True):
        if background:
            asyncio.create_task(asyncio.to_thread(self.container.remove, force=True))
        else:
            await asyncio.to_thread(self.container.remove, force=True)
