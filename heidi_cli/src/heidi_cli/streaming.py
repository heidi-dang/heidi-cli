from __future__ import annotations


from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn


class StreamingUI:
    def __init__(self, disable: bool = False):
        self.disable = disable
        self.console = Console()
        self.progress = None
        self.live = None
        self.current_task = ""
    
    def start(self, task: str):
        if self.disable:
            self.console.print(f"[cyan]{task}...[/cyan]")
            return
        
        self.current_task = task
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        )
        self.progress.start()
        self.task_id = self.progress.add_task(task, total=None)
    
    def update(self, status: str):
        if self.disable:
            self.console.print(f"  {status}")
            return
        
        if self.progress and self.task_id:
            self.progress.update(self.task_id, description=status)
    
    def stop(self, result: str = ""):
        if self.disable:
            if result:
                self.console.print(f"[green]{result}[/green]")
            return
        
        if self.progress:
            self.progress.stop()
        if result:
            self.console.print(Panel.fit(result, title="Done"))


def should_disable_live() -> bool:
    import os
    return os.environ.get("CI") == "true" or not hasattr(__import__('sys'), 'stdout.isatty') or not __import__('sys').stdout.isatty()
