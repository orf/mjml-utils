import subprocess
import time
from pathlib import Path
from typing import Annotated

import typer
import shutil
from rich.console import Console
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler, FileModifiedEvent

app = typer.Typer()
console = Console()


def run_mjml(*args: str) -> str:
    path = shutil.which("mjml")
    if not path:
        console.print("mjml command not found. Run `npm install -g mjml`")
        raise typer.Exit(code=1)
    return subprocess.check_output(
        [path, *args],
        stderr=subprocess.STDOUT,
        encoding="utf-8"
    )


class MJMLHandler(PatternMatchingEventHandler):
    def __init__(self):
        super().__init__(patterns=["*.mjml"], ignore_directories=True)

    def on_modified(self, event: FileModifiedEvent):
        file_path = Path(event.src_path)
        compile_mjml(file_path)


@app.command()
def watch(
        directory: Annotated[Path, typer.Argument(help="Directory to watch")],
):
    handler = MJMLHandler()
    observer = Observer()
    observer.schedule(handler, str(directory), recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    finally:
        observer.stop()
        observer.join()


def is_template(path: Path) -> bool:
    return "_template_" in path.name


@app.command()
def compile_all(path: Annotated[Path, typer.Argument(help="Path to directory")]):
    for mjml_file in path.rglob("*.mjml"):
        if not is_template(mjml_file):
            compile_mjml_file(mjml_file)


@app.command("compile")
def compile_mjml(path: Annotated[Path, typer.Argument(help="Path to mjml file", file_okay=True, dir_okay=False)]):
    if is_template(path):
        print("Template detected, compiling all templates")
        compile_all(path.parent)
    else:
        compile_mjml_file(path)


def compile_mjml_file(path: Path):
    template_contents = path.read_text()
    mjml_start_tag = template_contents.index("<mjml>")
    django_template_header = template_contents[0:mjml_start_tag]
    compiled_template = run_mjml(str(path))
    if compiled_template.startswith("<!-- FILE:"):
        compiled_template = "\n".join(compiled_template.split("\n", 1)[1:])

    # Add the template headers back
    compiled_template = f"{django_template_header}\n{compiled_template}"

    # Write the compiled template to the same directory as the mjml file
    compiled_path = path.parent / f"{path.stem}.html"
    compiled_path.write_text(compiled_template)
    print(f'Compiled template written to {compiled_path}')


if __name__ == '__main__':
    app()
