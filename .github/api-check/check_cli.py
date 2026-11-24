"""Static layer: check that the az and aws commands and flags in the repository exist in the installed CLIs."""
import argparse
import os
import re
import subprocess
import sys
from collections import namedtuple
from pathlib import Path

import common

REPO_ROOT = Path(__file__).resolve().parents[2]
EXCLUDED = ('.github/', 'docs/')
SHELL_TAGS = {'', 'bash', 'sh', 'shell', 'powershell', 'pwsh'}
KEYWORDS = {'if', 'then', 'else', 'elif', 'do', 'while', 'until'}
SEPARATORS = set('|&;()')
COMMAND_TOKEN = re.compile(r'^[a-z0-9][a-z0-9-]*$')
FLAG_TOKEN = re.compile(r'^(--[a-z0-9-]+)(?:=|$)')
HELP_FLAG = re.compile(r'--[a-z0-9-]+')
FENCE = re.compile(r'^\s*(`{3,}|~{3,})\s*([\w+-]*)')
# Top-level aws forms: first word -> argv that checks it.
AWS_TOP_LEVEL = {
    '--version': ['aws', '--version'],
    'configure': ['aws', 'configure', 'help'],
    'help': ['aws', 'help'],
}
HELP_TIMEOUT = 300

Command = namedtuple('Command', 'cloud words flags line')


def fenced_lines(text):
    """Yield (line number, line) for the shell fences of a Markdown file."""
    marker = None
    shell = False
    for number, line in enumerate(text.splitlines(), 1):
        fence = FENCE.match(line)
        if marker is None:
            if fence:
                marker, shell = fence.group(1), fence.group(2).lower() in SHELL_TAGS
        elif fence and fence.group(1)[0] == marker[0] and len(fence.group(1)) >= len(marker) \
                and line.strip() == fence.group(1):
            marker = None
        elif shell:
            yield number, line


def joined_lines(lines):
    """Drop comment lines and join `\\` and backtick continuations; yield (first line number, text)."""
    pending, start = '', 0
    for number, line in lines:
        text = line.strip()
        if not pending and text.startswith('#'):
            continue
        if not pending:
            start = number
        if text.endswith('\\') or text.endswith('`'):
            pending += text[:-1].rstrip() + ' '
            continue
        yield start, pending + text
        pending = ''
    if pending:
        yield start, pending


def tokenize(line):
    """Split a line into words (raw, quotes kept) and None separators; separators inside quotes do not count."""
    tokens, word, quote = [], '', None
    index = 0
    while index < len(line):
        char = line[index]
        if quote:
            word += char
            if char == '\\' and quote == '"' and index + 1 < len(line):
                index += 1
                word += line[index]
            elif char == quote:
                quote = None
        elif char in '"\'':
            quote = char
            word += char
        elif char == '\\' and index + 1 < len(line):
            index += 1
            word += char + line[index]
        elif char.isspace() or char in SEPARATORS:
            if char == '(' and word.endswith('$'):
                word = word[:-1]
            if word:
                tokens.append(word)
            word = ''
            if char in SEPARATORS:
                tokens.append(None)
        elif char == '#' and not word:
            break
        else:
            word += char
        index += 1
    if word:
        tokens.append(word)
    return tokens


def command_words(cloud, tokens):
    """Return the command words that follow `az` or `aws` in tokens (empty when none is recognisable)."""
    if cloud == 'aws' and tokens and tokens[0] in AWS_TOP_LEVEL:
        return (tokens[0],)
    words = []
    for token in tokens:
        if not COMMAND_TOKEN.match(token) or (cloud == 'aws' and len(words) == (3 if words[1:2] == ['wait'] else 2)):
            break
        words.append(token)
    if cloud == 'aws' and (len(words) < 2 or (words[1] == 'wait' and len(words) < 3)):
        return ()
    return tuple(words)


def extract_line(line, number):
    tokens = tokenize(line)
    segments, current = [], []
    for token in tokens + [None]:
        if token is None:
            segments.append(current)
            current = []
        else:
            current.append(token)
    for segment in segments:
        for index, token in enumerate(segment):
            if token not in ('az', 'aws'):
                continue
            previous = segment[index - 1] if index else None
            if previous is None or previous in KEYWORDS or previous == '!' or previous.endswith('='):
                rest = segment[index + 1:]
                words = command_words(token, rest)
                if words:
                    args = rest[1:] if words == ('--version',) else rest
                    flags = [m.group(1) for m in map(FLAG_TOKEN.match, args) if m]
                    yield Command(token, words, flags, number)
                break


def extract_commands(text, markdown):
    lines = fenced_lines(text) if markdown else enumerate(text.splitlines(), 1)
    for number, line in joined_lines(lines):
        yield from extract_line(line, number)


def tracked_files(root):
    names = subprocess.run(['git', 'ls-files', '*.md', '*.sh'], cwd=root, capture_output=True, text=True,
                           check=True).stdout.splitlines()
    return [name for name in names if not name.startswith(EXCLUDED)]


def argv_for(cloud, words):
    if cloud == 'aws':
        return AWS_TOP_LEVEL.get(words[0]) or ['aws', *words, 'help']
    return ['az', *words, '--help']


def run_help(argv):
    env = {**os.environ, 'AWS_PAGER': '', 'PAGER': 'cat'}
    done = subprocess.run(argv, shell=False, timeout=HELP_TIMEOUT, stdin=subprocess.DEVNULL, capture_output=True,
                          text=True, env=env)
    return done.returncode, done.stdout + done.stderr


def flag_listed(flag, known):
    """A flag exists when listed, or when it is a prefix of exactly one listed flag (as both CLIs accept)."""
    return flag in known or sum(other.startswith(flag) for other in known) == 1


def exercise_of(name):
    match = re.match(r'(\d+)-', name)
    return match.group(1) if match else None


def run(cloud, files, root, skip):
    """Write one row per command occurrence and per missing or skipped flag; return the counts."""
    prefix = {'azure': 'az', 'aws': 'aws'}[cloud]
    skipped = {entry['target']: entry['reason'] for entry in skip}
    found = []
    for name in files:
        text = (Path(root) / name).read_text(encoding='utf-8', errors='replace')
        for command in extract_commands(text, name.endswith('.md')):
            if command.cloud == prefix:
                found.append((name, command))
    cache = {}
    counts = {'found': len(found), 'checked': 0, 'missing': 0}
    if cloud == 'azure' and found:
        run_help(['az', 'config', 'set', 'extension.use_dynamic_install=yes_without_prompt'])
    for name, command in found:
        target = ' '.join([prefix, *command.words])
        where = dict(cloud=cloud, exercise=exercise_of(name), layer='static', file=name, line=command.line)
        if target in skipped:
            common.write_row(target=target, check='command', status='skipped', reason=skipped[target], **where)
            continue
        if target not in cache:
            counts['checked'] += 1
            try:
                code, output = run_help(argv_for(prefix, command.words))
            except (OSError, subprocess.TimeoutExpired) as error:
                code, output = None, str(error)
            cache[target] = (code, output, set(HELP_FLAG.findall(output)))
            if code not in (0, None):
                with common.log_path(f'static-{cloud}.log').open('a', encoding='utf-8') as log:
                    log.write(common.mask(f'$ {target}\n{output}\n'))
        code, output, known = cache[target]
        if code is None:
            common.write_row(target=target, check='command', status='infrastructure', error=output, **where)
            continue
        if code != 0:
            counts['missing'] += 1
            lines = output.strip().splitlines()
            common.write_row(target=target, check='command', status='missing-command',
                             error=lines[-1] if lines else '', **where)
            continue
        common.write_row(target=target, check='command', status='ok', **where)
        for flag in command.flags:
            flag_target = f'{target} {flag}'
            if flag_target in skipped:
                common.write_row(target=flag_target, check='flag', status='skipped', reason=skipped[flag_target],
                                 **where)
            elif not flag_listed(flag, known):
                counts['missing'] += 1
                common.write_row(target=flag_target, check='flag', status='missing-flag', **where)
    return counts


def main(argv=None, root=REPO_ROOT, files=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--cloud', choices=('azure', 'aws'), required=True)
    args = parser.parse_args(argv)
    skip = common.load_targets().get('skip') or []
    counts = run(args.cloud, tracked_files(root) if files is None else files, root, skip)
    print(f"{args.cloud}: found {counts['found']}, checked {counts['checked']}, missing {counts['missing']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
