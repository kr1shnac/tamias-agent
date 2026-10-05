import os
import sys
import argparse
from dotenv import load_dotenv
from openai import OpenAI

import json
import subprocess #run_shell

from rich.console import Console
from rich.markdown import Markdown
from rich.rule import Rule
from rich.text import Text
from rich.align import Align
from rich.panel import Panel

console = Console()

load_dotenv()

BASE_URL = os.environ.get("TAMIAS_BASE_URL", "https://openrouter.ai/api/v1")
MODEL = os.environ.get("AGENT_MODEL", "poolside/laguna-s-2.1:free")

client = OpenAI(
    base_url=BASE_URL,
    api_key=os.environ["OPENROUTER_API_KEY"]
)

history = []

#defining tool - telling AI about tool and what they do
TOOLS = [
    {
        "type": "function", #RUN SHELL
        "function": {
            "name": "run_shell",
            "description": "Run a shell command and return the output",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to run"
                    }
                },
                "required": ["command"]
            }
        } 
    }, {
        "type": "function",  #WRITE
        "function": {
            "name": "write_file",
            "description": "Write the file according to users input",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "understand the file path or location"
                    },
                    "content": {
                        "type": "string",
                        "description": "the AI return content will be extrated to write in file"
                    }
                },
                "required": ["file_path", "content"]
            }
        }
    }, {
        "type": "function", #EDIT
        "function": {
            "name": "edit_file",
            "description": "Find a specific piece of text in a file and replace it with new text. Use this to make surgical edits without rewriting the whole file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The path of the file to edit."
                    },
                    "old_text": {
                        "type": "string",
                        "description": "The exact text to find and replace."
                    },
                    "new_text": {
                        "type": "string",
                        "description": "The new text to replace it with."
                    }
                },
                "required": ["file_path", "old_text", "new_text"]
            }

        }
    }, {
        "type": "function", #READ
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file and return it as text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The path of the file to read. Example: main.py"
                    }
                },
                "required": ["file_path"]
            }
        }
    }, {
        "type": "function", #LIST
        "function": {
            "name": "list_directory",
            "description": "List all files and folder inside a directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The directory path to list. Use '.' for current directory."
                    }
                },
                "required": ["path"]
            }
        }
    }, {
        "type": "function", #CREATE_DIR
        "function": {
            "name": "create_directory",
            "description": "Create a new folder. Also creates any missing parent folders",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The folder path to create. Example: projects/my_app"
                    }
                },
                "required": ["path"]
            }
        }
    }, {
        "type": "function", #search in files
        "function": {
            "name": "search_in_files",
            "description": "Search for a word or a patter across all files in a directory. Returns every line that contain the match, with the file name and line number",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "The word or text to serch for."
                    },
                    "directory": {
                        "type": "string",
                        "description": "The directory to search inside. Use '.' for current directory."
                    }
                },
                "required": ["pattern", "directory"]
            }
        }
    }
]

#Tool EXECUTOR 

#COMMAND SHELL
def run_shell (command):
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True, #o/p as string not bytes
            timeout=60
        )

    except subprocess.TimeoutExpired:
        return "Error: command timed out after 60s"

    output = result.stdout #output

    if result.stderr: #error
        output = output + "\nError:\n" + result.stderr
    
    return output if output else "no output"



#WRITE
def write_file(file_path, content) :
    dir_name = os.path.dirname(file_path)

    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(str(content))

    return f"success, file '{file_path}' written completely"



#EDIT
def edit_file(file_path, old_text, new_text):
    try: 
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        if old_text not in content:
            return f"Error: could not find the text to replace in '{file_path}'"
        
        updated = content.replace(old_text, new_text, 1)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(updated)
        
        return f"Success: edit applied to '{file_path}'"

    except FileNotFoundError:
        return f"Error: file '{file_path}' not found"

    except Exception as e:
        return f"Error editing file: {str(e)}"



#READ
def read_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    
    except FileNotFoundError: 
        return f"Error: file '{file_path}' not found"

    except Exception as e:
        return f"Error reading file: {str(e)}"


#LIST_DIR
def list_directory(path):
    try: 
        items = os.listdir(path)
        
        if not items:
            return f"Directory '{path}' is empty"

        result = []

        for item in sorted(items):
            full = os.path.join(path, item)
            tag = "[DIR] " if os.path.isdir(full) else "[FILE]"
            result.append(f"{tag} {item}")
        
        return "\n".join(result)

    except FileNotFoundError:
        return f"Error: directory '{path}' not found"

    except Exception as e:
        return f"Error listing directory: {str(e)}"


#CREATE_DIR
def create_directory(path):
    try: 
        os.makedirs(path, exist_ok=True)
        return f"Success: directory '{path}' created"

    except Exception as e:
        return f"Error creating directory: {str(e)}"


#SERACH IN FILES - should read 
def search_in_files(pattern, directory):
    matches = []

    try:
        for root, dirs, files in os.walk(directory):

            # Skip hidden folders and __pycache__
            dirs[:] = [
                d for d in dirs
                if not d.startswith(".") and d != "__pycache__"
            ]

            for file in files:
                if file.endswith(
                    (".py", ".txt", ".md", ".json",
                     ".js", ".ts", ".html", ".css")
                ):
                    file_path = os.path.join(root, file)

                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            for line_num, line in enumerate(f, 1):
                                if pattern.lower() in line.lower():
                                    matches.append(
                                        f"{file_path}:{line_num} → {line.rstrip()}"
                                    )
                    except:
                        continue

        if not matches:
            return f"No matches found for '{pattern}' in '{directory}'."

        return "\n".join(matches)

    except Exception as e:
        return f"Error searching files: {str(e)}"


# TOOL DISPACTHER 

def dispatch_tool(tool_name, args):
    if tool_name == "run_shell":
        return run_shell(args["command"])
    elif tool_name == "write_file":
        return write_file(args["file_path"], args["content"])
    elif tool_name == "read_file":
        return read_file(args["file_path"])
    elif tool_name == "edit_file":
        return edit_file(args["file_path"], args["old_text"], args["new_text"])
    elif tool_name == "list_directory":
        return list_directory(args["path"])
    elif tool_name == "create_directory":
        return create_directory(args["path"])
    elif tool_name == "search_in_files":
        return search_in_files(args["pattern"], args["directory"])
    else:
        return f"Error: unknown tool '{tool_name}'"


#a broken tool call must never kill the agent - always hand back an "Error: ..."
def safe_tool_call(tool_name, raw_args):
    try:
        args = json.loads(raw_args) if raw_args else {}

        if not isinstance(args, dict):
            return {}, f"Error: arguments for '{tool_name}' must be a JSON object"

    except Exception as e:
        return {}, f"Error: could not parse arguments for '{tool_name}': {str(e)}"

    try:
        return args, dispatch_tool(tool_name, args)

    except Exception as e:
        return args, f"Error: {tool_name} failed: {str(e)}"


#-------------------------
#Welcome message
#the project name in block letters - T A M I A S
WORDMARK = """████████╗ █████╗ ███╗   ███╗██╗ █████╗ ███████╗
╚══██╔══╝██╔══██╗████╗ ████║██║██╔══██╗██╔════╝
   ██║   ███████║██╔████╔██║██║███████║███████╗
   ██║   ██╔══██║██║╚██╔╝██║██║██╔══██║╚════██║
   ██║   ██║  ██║██║ ╚═╝ ██║██║██║  ██║███████║
   ╚═╝   ╚═╝  ╚═╝╚═╝     ╚═╝╚═╝╚═╝  ╚═╝╚══════╝"""

COLOURS = [
    "bold bright_cyan",   # row 1
    "bold cyan",          # row 2
    "bold bright_blue",   # row 3
    "bold bright_magenta", # row 4
    "bold magenta",       # row 5
    "bold bright_magenta", # row 6
]


def print_banner():
    rows = WORDMARK.split("\n")
    wordmark = Text()

    for index, row in enumerate(rows):
        if index:
            wordmark.append("\n")

        wordmark.append(row, style=COLOURS[index % len(COLOURS)])

    wordmark.append("\n\na terminal coding agent\n", style="dim italic")
    wordmark.append(
        f"{MODEL} · {len(TOOLS)} tools · /quit to leave", style="dim"
    )

    console.print(
        Panel(
            Align.center(wordmark),
            border_style="cyan",
            padding=(1, 4)
        )
    )
    console.print()

#CLI
def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="agent.py",
        description="TAMIAS - a terminal coding agent"
    )

    parser.add_argument(
        "--task",
        help="run one task non-interactively, then exit"
    )

    parser.add_argument(
        "--max-steps",
        type=int,
        default=25, #max API calls per turn
        help="max API calls per turn (default: 25)"
    )

    args = parser.parse_args(argv)

    if args.max_steps < 1:
        parser.error("--max-steps must be at least 1")

    return args


#counters for the one line summary
def new_stats():
    return {"steps": 0, "prompt_tokens": 0, "completion_tokens": 0}


#one dim line after every API call - works when usage is missing
def log_step(step, response, stats):
    usage = getattr(response, "usage", None)
    prompt_tokens = getattr(usage, "prompt_tokens", None)
    completion_tokens = getattr(usage, "completion_tokens", None)

    stats["steps"] += 1

    if isinstance(prompt_tokens, int):
        stats["prompt_tokens"] += prompt_tokens

    if isinstance(completion_tokens, int):
        stats["completion_tokens"] += completion_tokens

    console.print(
        f"[dim]step {step} · model {getattr(response, 'model', None)} · "
        f"prompt {prompt_tokens} · completion {completion_tokens}[/dim]"
    )


#every tool call gets a card of its own
def print_tool_call(tool_name, target, result):
    failed = result.startswith("Error:")

    preview = result if len(result) <= 400 else result[:400] + "..."

    console.print(
        Panel(
            Text(preview, style="dim"),
            title=Text(
                f"⚙  {tool_name}",
                style="bold red" if failed else "bold yellow"
            ),
            subtitle=Text(str(target) or "-", style="dim"),
            border_style="red" if failed else "yellow",
            padding=(0, 1)
        )
    )


#errors and warnings get their own card
def print_error(label, message, style="red"):
    console.print(
        Panel(
            Text(str(message), style=style),
            title=Text(label, style=f"bold {style}"),
            border_style=style,
            padding=(0, 1)
        )
    )


#one user turn - returns "done", "error" or "cap"
def run_turn(user_input, max_steps, stats):
    checkpoint = len(history) #remember where this turn started
    history.append({"role": "user", "content": user_input})

    step = 0

    while True:
        if step >= max_steps: #out of steps, throw the whole turn away
            del history[checkpoint:]
            print_error("step limit", f"step cap of {max_steps} reached",
                        style="yellow")
            return "cap"

        step += 1

        with console.status("[dim]thinking…[/dim]"):
            try :
                response = client.chat.completions.create(
                            model=MODEL,
                            messages=[
                                {
                                    "role": "system",
                                    "content": (
                                        "You are TAMIAS, a helpful terminal coding agent. "
                                        "You can read files, write files, edit files, run shell commands, "
                                        "list directories, create folders, and search across files. "
                                        "When given a task, think step by step and use your tools to complete it. "
                                        "Always verify your work — after writing or editing a file, read it back. "
                                        "After running code, check the output for errors and fix them."
                                    )
                                }
                            ] + history,
                            tools=TOOLS
                )

            except Exception as e:
                del history[checkpoint:] #undo the turn, history stays valid
                print_error("api error", e)
                return "error"

        log_step(step, response, stats)

        message = response.choices[0].message

        # did the AI want a tool or just reply

        if message.tool_calls:

            tool_calls_list = []

            for tc in message.tool_calls:
                one_item = {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }

                tool_calls_list.append(one_item)

            history.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": tool_calls_list
            })

            for tc in message.tool_calls:
                tool_name = tc.function.name

                #every tool call gets a result back, even a broken one
                args, result = safe_tool_call(tool_name, tc.function.arguments)

                target = list(args.values())[0] if args else ""

                print_tool_call(tool_name, target, result)

                history.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result
                })

                continue #take tool context goes back to input

        else:
            reply = message.content

            history.append({
                "role": "assistant",
                "content": reply
            })

            console.print(Rule(Text("TAMIAS ›", style="bold magenta"),
                               style="magenta"))
            console.print(Markdown(reply or ""))
            console.print()

            return "done" #exit inner loop


#one task, no questions asked, then one line summary
def run_task(task, max_steps):
    stats = new_stats()
    outcome = run_turn(task, max_steps, stats)

    console.print(
        f"[dim]steps: {stats['steps']} · "
        f"prompt tokens: {stats['prompt_tokens']} · "
        f"completion tokens: {stats['completion_tokens']}[/dim]"
    )

    return 1 if outcome in ("error", "cap") else 0


#what can I type
HELP = """[bold green]/quit[/bold green]   leave TAMIAS
[bold green]/help[/bold green]   this list

[bold]tools[/bold]
  run_shell          run a shell command (60s timeout)
  read_file          read a file
  write_file         write a file
  edit_file          replace exact text in a file
  list_directory     list a directory
  create_directory   make a folder
  search_in_files    grep across a directory

[bold]flags[/bold]
  --task "text"      do one task, print a summary, exit
  --max-steps N      API calls per turn (default 25)"""


def print_help():
    console.print(
        Panel(
            Text(HELP),
            title=Text("help", style="bold cyan"),
            border_style="cyan",
            padding=(0, 2)
        )
    )


def goodbye():
    console.print(
        Align.center(Text("see you soon · /quit", style="dim"))
    )


#ask, answer, ask again
def interactive_loop(max_steps):
    while True:
        try:
            user_input = console.input("[bold green]You ›[/bold green]").strip()

        except (EOFError, KeyboardInterrupt):
            goodbye()
            return 0

        if not user_input:
            continue;

        if user_input == "/quit":
            goodbye()
            return 0

        if user_input == "/help":
            print_help()
            continue;

        run_turn(user_input, max_steps, new_stats())


def main(argv=None):
    print_banner()

    args = parse_args(argv)

    if args.task: #no chat, just do it and leave
        return run_task(args.task, args.max_steps)

    return interactive_loop(args.max_steps)


if __name__ == "__main__":
    sys.exit(main())
