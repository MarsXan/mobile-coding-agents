"""Split a shell command line into the simple commands it would run.

This is a tripwire, not a shell: it understands quoting, separators,
command substitution, `sh -c` strings, heredocs and the common wrappers well
enough that `bundle exec fastlane release`, `git -C . push --force` and
`sh -c 'rm -rf ~'` are all seen for what they are. When the text cannot be
parsed, `split` returns None and the caller falls back to a plain text scan.
"""

import re

SHELLS = ("sh", "bash", "zsh", "dash", "ksh", "fish")

# Words that introduce a command without being one.
_KEYWORDS = frozenset({"{", "}", "(", ")", "!", "then", "do", "else", "elif", "if", "while", "until", "fi", "done", "time"})

# wrapper -> number of following positional arguments to drop (flags are
# always dropped). `None` means "drop flags only".
_WRAPPERS = {
    "sudo": 0, "doas": 0, "nohup": 0, "nice": 0, "command": 0, "builtin": 0,
    "exec": 0, "caffeinate": 0, "stdbuf": 0, "xargs": 0, "noglob": 0,
    "rtk": 0, "xcrun": 0, "timeout": 1, "arch": 0, "ionice": 0, "setsid": 0,
}
_WRAPPER_FLAGS_WITH_VALUE = {
    "sudo": {"-u", "-g", "-C", "-h", "-p", "-U"},
    "nice": {"-n"},
    "xcrun": {"--sdk", "-sdk", "--toolchain", "-toolchain"},
    "timeout": {"-s", "--signal", "-k", "--kill-after"},
    "arch": {"-arch"},
    "caffeinate": {"-t", "-w"},
    "xargs": {"-n", "-I", "-P", "-L", "-d", "-s"},
}

# A heredoc body is data, not commands. Group 3 keeps the rest of the line that
# opened it (`cat <<EOF | sh` still pipes into a shell).
_HEREDOC = re.compile(r"<<-?[ \t]*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1([^\n]*)\n(?:.*?\n)??[ \t]*\2[ \t]*(?=\n|$)", re.S)


class Command(object):
    def __init__(self, argv, piped_from=None, sudo=False):
        self.argv = argv
        self.piped_from = piped_from      # program name of the previous pipeline stage
        self.sudo = sudo

    @property
    def prog(self):
        return self.argv[0] if self.argv else ""

    @property
    def args(self):
        return self.argv[1:]

    def __repr__(self):
        return "Command(%r)" % (self.argv,)


def _tokenize(text):
    """Return (list of (words, operator_before), nested_command_strings).

    Raises ValueError on an unterminated quote or substitution.
    """
    commands, nested = [], []
    words, word, has_word = [], [], False
    op_before = ""
    i, n = 0, len(text)
    skip_next_word = False

    def end_word():
        nonlocal word, has_word, skip_next_word
        if has_word:
            if skip_next_word:
                skip_next_word = False
            else:
                words.append("".join(word))
        word, has_word = [], False

    def end_command(op):
        nonlocal words, op_before
        end_word()
        if words:
            commands.append((words, op_before))
        words = []
        op_before = op

    def read_balanced(start, open_ch, close_ch):
        depth, j = 1, start
        while j < n:
            c = text[j]
            if c == "\\":
                j += 2
                continue
            if c == "'":
                k = text.find("'", j + 1)
                if k < 0:
                    raise ValueError("unterminated quote")
                j = k + 1
                continue
            if c == open_ch:
                depth += 1
            elif c == close_ch:
                depth -= 1
                if depth == 0:
                    return text[start:j], j + 1
            j += 1
        raise ValueError("unterminated substitution")

    while i < n:
        c = text[i]
        if c == "\\":
            if i + 1 < n and text[i + 1] == "\n":
                i += 2
                continue
            if i + 1 < n:
                word.append(text[i + 1])
                has_word = True
            i += 2
            continue
        if c == "'":
            k = text.find("'", i + 1)
            if k < 0:
                raise ValueError("unterminated quote")
            word.append(text[i + 1: k])
            has_word = True
            i = k + 1
            continue
        if c == '"':
            j = i + 1
            while True:
                if j >= n:
                    raise ValueError("unterminated quote")
                d = text[j]
                if d == "\\" and j + 1 < n:
                    word.append(text[j + 1])
                    j += 2
                    continue
                if d == "$" and j + 1 < n and text[j + 1] == "(":
                    inner, j = read_balanced(j + 2, "(", ")")
                    nested.append(inner)
                    word.append("$()")
                    continue
                if d == "`":
                    k = text.find("`", j + 1)
                    if k < 0:
                        raise ValueError("unterminated backtick")
                    nested.append(text[j + 1: k])
                    word.append("$()")
                    j = k + 1
                    continue
                if d == '"':
                    break
                word.append(d)
                j += 1
            has_word = True
            i = j + 1
            continue
        if c == "$" and i + 1 < n and text[i + 1] == "(":
            inner, i = read_balanced(i + 2, "(", ")")
            nested.append(inner)
            word.append("$()")
            has_word = True
            continue
        if c == "`":
            k = text.find("`", i + 1)
            if k < 0:
                raise ValueError("unterminated backtick")
            nested.append(text[i + 1: k])
            word.append("$()")
            has_word = True
            i = k + 1
            continue
        if c == "#" and not has_word:
            k = text.find("\n", i)
            i = n if k < 0 else k
            continue
        if c in " \t":
            end_word()
            i += 1
            continue
        if c in ";\n":
            end_command(";")
            i += 1
            continue
        if c == "&":
            if text[i: i + 2] == "&&":
                end_command("&&")
                i += 2
                continue
            if text[i: i + 2] == "&>":
                end_word()
                skip_next_word = True
                i += 3 if text[i: i + 3] == "&>>" else 2
                continue
            end_command("&")
            i += 1
            continue
        if c == "|":
            if text[i: i + 2] == "||":
                end_command("||")
                i += 2
                continue
            end_command("|")
            i += 2 if text[i: i + 2] == "|&" else 1
            continue
        if c in "()":
            end_command(";")
            skip_next_word = False      # `<(cmd)`: the parenthesis is not a redirect target
            i += 1
            continue
        if c in "<>":
            # A redirection: drop a leading file-descriptor word and the target.
            if has_word and "".join(word).isdigit():
                word, has_word = [], False
            else:
                end_word()
            j = i
            while j < n and text[j] in "<>":
                j += 1
            if j < n and text[j] == "&":
                j += 1
                while j < n and (text[j].isdigit() or text[j] == "-"):
                    j += 1
                i = j
                continue
            skip_next_word = True
            i = j
            continue
        word.append(c)
        has_word = True
        i += 1
    end_command("")
    return commands, nested


def _basename(prog):
    return prog.rsplit("/", 1)[-1]


def _strip(words):
    """Drop env assignments, keywords and wrappers. Returns (argv, used_sudo)."""
    sudo = False
    words = list(words)
    while words:
        head = words[0]
        if head in _KEYWORDS:
            words.pop(0)
            continue
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", head):
            words.pop(0)
            continue
        base = _basename(head)
        if base == "env":
            words.pop(0)
            while words and (words[0].startswith("-") or re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", words[0])):
                flag = words.pop(0)
                if flag in ("-u", "--unset", "-C", "--chdir", "-S") and words:
                    words.pop(0)
            continue
        if base in _WRAPPERS:
            if base in ("sudo", "doas"):
                sudo = True
            if base == "xcrun" and len(words) > 1 and words[1] in ("--find", "-f", "--show-sdk-path", "--show-sdk-version", "--version"):
                break
            words.pop(0)
            with_value = _WRAPPER_FLAGS_WITH_VALUE.get(base, set())
            while words and words[0].startswith("-") and words[0] != "-":
                flag = words.pop(0)
                if flag == "--":
                    break
                if flag in with_value and words:
                    words.pop(0)
            for _ in range(_WRAPPERS[base]):
                if words:
                    words.pop(0)
            if base == "rtk" and words and words[0] == "proxy":
                words.pop(0)
            continue
        if base == "bundle" and len(words) > 1 and words[1] == "exec":
            words = words[2:]
            continue
        if base == "fvm" and len(words) > 1 and words[1] in ("flutter", "dart"):
            words = words[1:]
            continue
        if base in ("mise", "asdf") and len(words) > 1 and words[1] in ("exec", "x"):
            words = words[2:]
            while words and words[0] != "--" and (words[0].startswith("-") or "@" in words[0]):
                words.pop(0)
            if words and words[0] == "--":
                words.pop(0)
            continue
        break
    if words:
        words[0] = _basename(words[0])
    return words, sudo


def split(text, _depth=0):
    """Return every simple command in `text` as a list of Command, or None."""
    if _depth > 4:
        return []
    text = _HEREDOC.sub(lambda m: " " + m.group(3), text)
    try:
        raw_commands, nested = _tokenize(text)
    except ValueError:
        return None
    out = []
    previous_prog = None
    for words, op_before in raw_commands:
        argv, sudo = _strip(words)
        if not argv:
            previous_prog = None
            continue
        piped_from = previous_prog if op_before in ("|",) else None
        out.append(Command(argv, piped_from=piped_from, sudo=sudo))
        previous_prog = argv[0]
        if argv[0] in SHELLS:
            # `sh -c '...'`, `bash -lc '...'`: the string is a command line too.
            for index in range(1, len(argv) - 1):
                if re.match(r"^-[A-Za-z]*c$", argv[index]):
                    inner = split(argv[index + 1], _depth + 1)
                    if inner is None:
                        return None
                    out.extend(inner)
                    break
        elif argv[0] == "eval" and len(argv) > 1:
            inner = split(" ".join(argv[1:]), _depth + 1)
            if inner is None:
                return None
            out.extend(inner)
    for inner_text in nested:
        inner = split(inner_text, _depth + 1)
        if inner is None:
            return None
        out.extend(inner)
    return out
