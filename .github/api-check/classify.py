"""Pure classification of AWS Emulator results for the daily API check; the callers write the rows."""
import json
import re

from run_azure_targets import SAMPLE_MARKER, classify_sample

NOT_COVERED = re.compile(r'NotImplemented|\b501\b')
TRACEBACK = 'Traceback (most recent call last):'
DOT_EDGE = re.compile(r'"([^"]+)"\s*->\s*"([^"]+)"')


def _row(exercise, status, target, check, file=None, line=None, error=None, reason=None):
    return {'cloud': 'aws', 'exercise': exercise, 'layer': 'emulator', 'target': target, 'file': file,
            'line': line, 'check': check, 'status': status, 'error': error, 'reason': reason}


def _aws_gaps(gaps, exercise):
    return [gap for gap in gaps if gap.get('cloud') == 'aws' and str(gap['exercise']) == str(exercise)]


def _find_gap(gaps, target, text):
    for gap in gaps:
        if gap.get('target') and re.search(gap['target'], target) and re.search(gap.get('pattern') or '', text):
            return gap
    return None


def _operation(argv):
    return [arg for arg in argv if not arg.startswith('-')][:2]


def _is_waiting(operation):
    return operation[1:2] == ['wait'] or operation == ['cloudformation', 'deploy']


def _first_line(text):
    return next((line for line in text.splitlines() if line.strip()), '')


_RANK = {'ok': 0, 'newly-covered': 1, 'not-covered': 2, 'drift': 3}


def _worst(rows):
    """Worst status of the rows; `consequential` rows do not raise it."""
    return max((row['status'] for row in rows), key=lambda status: _RANK.get(status, 0), default='ok')


def classify_script(exercise, script, calls, gaps, extra_rows=()):
    """Rows for the failing calls of one script (raw-log entries) and newly-covered gaps, then `extra_rows`
    (e.g. a sample row), then one closing row with check `run` (the pending row's key) holding the worst status."""
    gaps = _aws_gaps(gaps, exercise)
    rows = []
    seen_not_covered = False
    for call in calls:
        operation = _operation(call['argv'])
        check = ' '.join(operation)
        failed = call['timed_out'] or call['exit'] != 0
        if not failed:
            command = ' '.join(call['argv'])
            for gap in gaps:
                if gap.get('target') and re.search(gap['target'], command):
                    rows.append(_row(exercise, 'newly-covered', script, check, script, call['line'],
                                     reason=gap['reason']))
            continue
        error = _first_line(call['stderr']) or ('timeout' if call['timed_out'] else f"exit {call['exit']}")
        reason = None
        gap = _find_gap(gaps, ' '.join(call['argv']), call['stderr'])
        if NOT_COVERED.search(call['stderr']):
            status = 'not-covered'
        elif call['timed_out']:
            status, error = ('not-covered', 'timeout') if _is_waiting(operation) else ('drift', 'timeout')
        elif gap:
            status, reason = 'not-covered', gap['reason']
        else:
            status = 'drift'
        if seen_not_covered:
            status = 'consequential'
        seen_not_covered = seen_not_covered or status == 'not-covered'
        rows.append(_row(exercise, status, script, check, script, call['line'], error, reason))
    call_failures = sum(row['status'] not in ('newly-covered', 'ok') for row in rows)
    rows.extend(extra_rows)
    failures = sum(row['status'] not in ('newly-covered', 'ok') for row in rows)
    error = None
    if failures:
        error = 'run_sample failed' if failures == 1 and not call_failures else f'{failures} calls failed'
    rows.append(_row(exercise, _worst(rows), script, 'run', error=error))
    return rows


def classify_sample_output(exercise, stdout, gaps):
    """One row for a boto3 sample's output: `drift` on the error marker, or on the last traceback's exception
    line, unless a gap matches it."""
    sample_gaps = [gap for gap in _aws_gaps(gaps, exercise) if gap.get('pattern')]
    status, error, reason = classify_sample(0, stdout, sample_gaps)
    if SAMPLE_MARKER not in stdout and TRACEBACK in stdout:
        lines = stdout[stdout.rindex(TRACEBACK):].splitlines()[1:]
        error = next((line for line in lines if line and not line[0].isspace()), '')
        gap = next((gap for gap in sample_gaps if re.search(gap['pattern'], error)), None)
        status, reason = ('not-covered', gap['reason']) if gap else ('drift', None)
    return _row(exercise, status, 'sample', 'run_sample', error=error, reason=reason)


def _node(name):
    name = re.sub(r'^\[root\] ', '', name)
    name = re.sub(r' \((expand|close)\)$', '', name)
    return re.sub(r'\[[^\]]*\]$', '', name)


def _dependencies(dot):
    """Map each node to the nodes it depends on (edges point from dependent to dependency)."""
    edges = {}
    for source, target in DOT_EDGE.findall(dot):
        if not target.startswith('[root] provider['):
            edges.setdefault(_node(source), set()).add(_node(target))
    return edges


def _depends_on(address, edges, roots):
    pending, seen = [address], set()
    while pending:
        for dependency in edges.get(pending.pop(), ()):
            if dependency in roots:
                return True
            if dependency not in seen:
                seen.add(dependency)
                pending.append(dependency)
    return False


def _diagnostics(lines):
    for line in lines:
        try:
            item = json.loads(line)
        except ValueError:
            continue
        if item.get('type') == 'diagnostic' and item['diagnostic'].get('severity') == 'error':
            yield item['diagnostic']


def _completed(lines):
    for line in lines:
        try:
            item = json.loads(line)
        except ValueError:
            continue
        address = ((item.get('hook') or {}).get('resource') or {}).get('addr')
        if str(item.get('type', '')).endswith('_complete') and address:
            yield address


def classify_terraform(exercise, apply_lines, graph_dot, gaps, timed_out=False):
    """Rows for `terraform apply -json` output lines and the `terraform graph` DOT text."""
    gaps = _aws_gaps(gaps, exercise)
    if timed_out:
        return [_row(exercise, 'drift', 'terraform apply', 'apply', error='timeout')]
    errors = [(diag.get('address') or 'terraform apply', f"{diag.get('summary', '')}: {diag.get('detail', '')}", diag)
              for diag in _diagnostics(apply_lines)]
    statuses = {}
    for address, text, _ in errors:
        gap = _find_gap(gaps, address, text)
        if NOT_COVERED.search(text):
            statuses[address] = ('not-covered', None)
        elif gap:
            statuses[address] = ('not-covered', gap['reason'])
    edges = _dependencies(graph_dot)
    roots = set(statuses)
    rows = []
    for address, text, diag in errors:
        status, reason = statuses.get(address) or (
            ('consequential', None) if _depends_on(_node(address), edges, roots) else ('drift', None))
        rows.append(_row(exercise, status, address, 'apply', error=diag.get('summary') or text, reason=reason))
    failed = {address for address, _, _ in errors}
    for address in dict.fromkeys(_completed(apply_lines)):
        for gap in gaps:
            if gap.get('target') and address not in failed and re.search(gap['target'], address):
                rows.append(_row(exercise, 'newly-covered', address, 'apply', reason=gap['reason']))
    # Closing row on the configuration's key; an address-less error already sits there and keeps its text.
    own = next((row for row in rows if row['target'] == 'terraform apply' and row['status'] != 'newly-covered'), None)
    error = own['error'] if own else (f'{len(errors)} errors' if errors else None)
    rows.append(_row(exercise, _worst(rows), 'terraform apply', 'apply', error=error))
    return rows
