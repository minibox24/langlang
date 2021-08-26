import asyncio
import aiohttp
import time

LANGUAGES = {
    "bash": "echo ok",
    "c": '#include <stdio.h>\nint main() { printf("ok"); }',
    "cpp": '#include <iostream>\nint main() { std::cout << "ok"; }',
    "csharp": 'System.Console.WriteLine("ok");',
    "go": 'package main\nimport "fmt"\nfunc main() { fmt.Println("ok") }',
    "java": 'class Main { public static void main(String[] args) { System.out.println("ok"); } }',
    "javascript": 'console.log("ok")',
    "kotlin": 'fun main() { println("ok") }',
    "python": 'print("ok")',
    "text": "ok",
    "typescript": 'console.log("ok")',
}


async def test(language):
    t = time.time()

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:5000/eval",
            json={"language": language, "code": LANGUAGES[language]},
        ) as res:
            data = await res.json()

            if data["result"] == "ok":
                print(f"{language}: ok ({round(time.time() - t, 2)}s)")
            else:
                print(f"{language}: error ({round(time.time() - t, 2)}s)")


async def main():
    print(f"test {len(LANGUAGES)} languages\n")

    await asyncio.gather(*[test(language) for language in LANGUAGES])

    print("\ndone")


asyncio.run(main())
