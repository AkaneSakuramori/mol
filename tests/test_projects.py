"""Regression test for the reference Ulang projects under projects/.

Each project is a substantial, self-contained Ulang program. This test pins its output
and verifies it runs identically on the tree-walking interpreter and the bytecode VM, and
that the self-hosted compiler can compile it to bytecode. These programs are the
real-world validation for the language and toolchain (see docs/2.0-findings.md).
"""

import os
import sys
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ULANG = os.path.join(ROOT, "src", "ulang.py")
PROJECTS = os.path.join(ROOT, "projects")


CALC_EXPECTED = '1 + 2 * 3  =>  7.0\n(1 + 2) * 3  =>  9.0\n10 / 4  =>  2.5\n2 + 3 * 4 - 5  =>  9.0\nx = 6  =>  6.0\ny = 7  =>  7.0\nx * y + 1  =>  43.0\n-x + 100  =>  94.0\nx = 22.5  =>  22.5\nx * 2  =>  45.0\n100 % 7  =>  2.0\n'
WORDSTATS_EXPECTED = 'total words:  24\nunique words: 14\nlongest word: amused\ntop words:\n  the: 5\n  quick: 3\n  fox: 3\n  dog: 3\n  brown: 1\n'
JSONFMT_EXPECTED = '{\n  "name": "ulang",\n  "version": 2,\n  "stable": true,\n  "keywords": [\n    "compiled",\n    "typed",\n    "self-hosted"\n  ],\n  "counts": {\n    "stages": 8,\n    "suites": 28\n  },\n  "notes": null\n}\n'
LIFE_EXPECTED = 'generation 0:\n.#....\n..#...\n###...\n......\n......\n......\n\ngeneration 1:\n......\n#.#...\n.##...\n.#....\n......\n......\n\ngeneration 2:\n......\n..#...\n#.#...\n.##...\n......\n......\n\ngeneration 3:\n......\n.#....\n..##..\n.##...\n......\n......\n\n'
RPN_EXPECTED = '3 4 +  =>  7\n5 1 2 + 4 * + 3 -  =>  14\n10 2 /  =>  5\n7 0 /  =>  error: division by zero\n2 3 4 * +  =>  14\n1 +  =>  error: stack underflow\n1 2 3  =>  error: too many values\n9 3 % 2 *  =>  0\n'
TABLE_EXPECTED = '+----------+-------+-------------+\n| language | typed | self-hosted |\n+----------+-------+-------------+\n| ulang    | yes   | compiler    |\n| python   | no    | yes         |\n| c        | yes   | yes         |\n+----------+-------+-------------+\n'
KVSTORE_EXPECTED = 'SET a 10  ->  OK\nSET b 20  ->  OK\nGET a  ->  10\nINCR a 5  ->  15\nGET a  ->  15\nEXISTS b  ->  true\nEXISTS z  ->  false\nDEL b  ->  deleted\nGET b  ->  ERR no such key: b\nCOUNT  ->  1\nSET c notanumber  ->  ERR value must be an integer\nINCR counter 1  ->  1\nINCR counter 1  ->  2\nGET counter  ->  2\nKEYS  ->  a, counter\nPING  ->  ERR unknown command: PING\n'
STATS_EXPECTED = 'n:        6\nmean:     18.0\nvariance: 151.66666666666666\nstddev:   12.315302134607444\nmin:      4.0\nmax:      42.0\nmedian:   15.5\n'
PROGRAMS = [
    ("calc/calc.ul", CALC_EXPECTED),
    ("wordstats/wordstats.ul", WORDSTATS_EXPECTED),
    ("jsonfmt/jsonfmt.ul", JSONFMT_EXPECTED),
    ("life/life.ul", LIFE_EXPECTED),
    ("rpn/rpn.ul", RPN_EXPECTED),
    ("table/table.ul", TABLE_EXPECTED),
    ("kvstore/kvstore.ul", KVSTORE_EXPECTED),
    ("stats/stats.ul", STATS_EXPECTED),
]


def _run(cmd, path):
    r = subprocess.run([sys.executable, ULANG, cmd, os.path.join(PROJECTS, path)],
                       capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def run():
    failed = 0
    checked = 0
    for rel, expected in PROGRAMS:
        checked += 1
        code, out, err = _run("run", rel)
        if code == 0 and out == expected:
            print(f"ok   {rel}: interpreter output matches")
        else:
            print(f"FAIL {rel}: interpreter output\n--- expected ---\n{expected}\n--- got ---\n{out}\n{err}")
            failed += 1

        checked += 1
        vcode, vout, verr = _run("runvm", rel)
        if vcode == 0 and vout == out:
            print(f"ok   {rel}: VM output matches interpreter")
        else:
            print(f"FAIL {rel}: VM output differs from interpreter\n{verr}")
            failed += 1

        checked += 1
        scode, sout, serr = _run("selfhost", rel)
        if scode == 0 and "code " in sout:
            n = sout.count("code ")
            print(f"ok   {rel}: self-hosted compiler emits bytecode ({n} functions)")
        else:
            print(f"FAIL {rel}: self-hosted compiler failed\n{sout}\n{serr}")
            failed += 1

    print(f"\n{checked - failed}/{checked} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
