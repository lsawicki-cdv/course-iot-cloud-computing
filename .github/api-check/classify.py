"""Pure classification of AWS Emulator results for the daily API check; the callers write the rows."""
import json
import re

from run_azure_targets import classify_sample

NOT_COVERED = re.compile(r'NotImplemented|\b501\b')
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


def classify_script(exercise, script, calls, gaps):
    """Rows for the failing calls of one script (raw-log entries), newly-covered gaps and, when nothing
    failed, one `ok` row with check `run`."""
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
    if not any(row['status'] != 'newly-covered' for row in rows):
        rows.append(_row(exercise, 'ok', script, 'run'))
    return rows


def classify_sample_output(exercise, stdout, gaps):
    """One row for a boto3 sample's stdout: `drift` on the error marker unless a gap matches its message."""
    sample_gaps = [gap for gap in _aws_gaps(gaps, exercise) if gap.get('pattern')]
    status, error, reason = classify_sample(0, stdout, sample_gaps)
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
    errors = [(diag['address'], f"{diag.get('summary', '')}: {diag.get('detail', '')}", diag)
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
    if not errors:
        rows.append(_row(exercise, 'ok', 'terraform apply', 'apply'))
    return rows
