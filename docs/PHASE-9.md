# Phase 9 · Measured load and recovery

The phase used a separate loopback server, temporary SQLite files and generated records. It did not load test the public tunnel. The workload used 1,000 people per monthly snapshot, eight independently authenticated sessions, three rounds per session and five operations per round. Each session selected its own report date, read overview, queue and case detail, and downloaded Excel. Each timed operation includes the response body. The platform was macOS 15.7.9 on x86_64 and CPython 3.14.6. Results are one before/after pair, not a capacity guarantee.

| Operation | Before p95 | After p95 | Samples per run |
| --- | ---: | ---: | ---: |
| Select snapshot | 2,860.06 ms | 167.28 ms | 24 |
| Overview | 14,505.82 ms | 448.21 ms | 24 |
| Casework queue | 4,740.50 ms | 65.95 ms | 24 |
| Case details | 4,488.45 ms | 43.98 ms | 24 |
| Excel download | 6,755.30 ms | 1,075.69 ms | 24 |

Both runs completed 120 timed operations with zero request errors. Workbook checks covered the selected month. In the second run, online backup during load took 0.163 seconds, and isolated startup from the copy, invalidating its eight sessions, and verification of the report via fresh authentication took 0.430 seconds. The old session token could not download Excel. A failed synthetic import preserved the selected workbook byte for byte. The measured backup was 5,750,784 bytes.

The app now initializes the SQLite schema at startup rather than on every HTTP request. It reuses at most three evaluated synthetic snapshots with no more than 30,000 source rows each. The cache key combines the accepted snapshot ID and digest. Authorization is reapplied after loading the snapshot and session data stays separate. Local uploaded datasets bypass the snapshot cache.

## Repeat the measurement

```sh
python3 -m cockpit.reliability --workers 8 --rounds 3 --people 1000
```

This command creates and removes its own synthetic database and listens only on a temporary loopback port. The [earlier million-row CLI benchmark](VERIFICATION.md) is a separate single-user import/evaluation/export measurement. Multi-instance failover, throughput on municipal hardware, network latency under load and the organization’s recovery targets still require deployment-specific testing.
