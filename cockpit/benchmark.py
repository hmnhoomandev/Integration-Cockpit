"""Measure generation, snapshot import, evaluation, and Excel serialization."""
from pathlib import Path
from resource import getrusage, RUSAGE_SELF
from tempfile import TemporaryDirectory
from time import perf_counter
import argparse
import json
import sys

from . import data, rules, ui, xlsx


def benchmark(people):
    with TemporaryDirectory() as work:
        db = data.connect(Path(work)/'measure.sqlite')
        month = data.MONTHS[-1]
        start = perf_counter()
        sources = data.seed(month,people)
        generated = perf_counter()
        identifier,_ = data.load_files(db,sources.values(),month,'synthetic')
        imported = perf_counter()
        snapshot,rows = data.get_snapshot(db,identifier)
        cases = rules.evaluate(snapshot,rows)
        evaluated = perf_counter()
        blob = xlsx.write(ui.export(1,snapshot,cases,'judge'))
        exported = perf_counter()
        actual = sum(json.loads(snapshot['inspected']).values())
        assert len(cases)==people and sum(rules.counts(cases,0).values())==people
        db.close()
        metric = getrusage(RUSAGE_SELF).ru_maxrss / (1024**2 if sys.platform=='darwin' else 1024)
        return {'people':people,'source_rows':actual,'generate_seconds':round(generated-start,2),
          'import_seconds':round(imported-generated,2),'evaluate_seconds':round(evaluated-imported,2),
          'export_seconds':round(exported-evaluated,2),'export_bytes':len(blob),'peak_rss_mib':round(metric,1)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('people',type=int,nargs='+')
    for count in parser.parse_args().people:
        print(json.dumps(benchmark(count)),flush=True)
