# CECS 327 – Assignment 3: Total-Order Multicast for Replication

## Files

| File | Description |
|---|---|
| `messages.py` | Message constructors: `TOBCAST`, `ACK`, `oper` |
| `replica.py` | **Part A** – `Replica` class: Lamport clock, holdback queue, delivery rule, key-value store |
| `driver.py` | **Part B** – Test harness: `NetworkSimulator`, `ReplicaProxy`, three required experiments |
| `part_c.md` | **Part C** – Written question answers |
| `run.log` | Captured terminal output from all three experiments |

## How to Run
**Requirements:** Python 3.8+, no external packages.

```bash
# Run all three experiments
python driver.py

# Capture output to a log file
python driver.py > run.log
```

## Architecture

```
Clients
   |         \         (clients can send to any replica)
   v          v
+----+  +----+  +----+  +----+
| R0 |  | R1 |  | R2 |  | R3 |
+----+  +----+  +----+  +----+
   \       |       /       |
    \------|---/-----------|
       total-order multicast
  (TOBCAST + ACK, holdback queues,
   deliver only when safe)
```

### Message flow for one client update

```
Client          R0                  R1 / R2 / R3
  |              |                       |
  |--request --> |                       |
  |              |-- TOBCAST(uid,op,ts) ->|
  |              |                       |
  |              |<-- ACK(uid,ts) --------|
  |              |                       |
  |   [holdback queue, sorted by (ts, sender_id)]
  |   [deliver when max_seen[k] > msg.ts for all k]
  |              |                       |
  |        apply_op()             apply_op()
  |        (same order at every replica)
```

### Key data structures per replica

| Field | Description |
|---|---|
| `clock_i` | Lamport logical clock; incremented on send and receive |
| `holdback_queue` | Messages waiting to be delivered, sorted by `(ts, sender_id)` |
| `max_seen[k]` | Largest timestamp seen in any message from replica `k` |
| `store` | Replicated key-value dictionary |
| `delivered_log` | Ordered list of `update_id`s, used to verify consistent delivery sequence |

### Delivery rule

A message `m` at the head of the holdback queue is delivered only when:

```
for all k:  max_seen[k] > m.ts[0]
```

This guarantees no replica will later send a message with a smaller timestamp, ensuring a globally consistent total order.

## Experiments (Part B)

| # | Scenario | Replicas | Updates |
|---|---|---|---|
| 1 | Concurrent conflicting writes (`put`, `append`, `put`) to the same key | 3 | 3 |
| 2 | High contention (`incr` on one counter) | 4 | 30 |
| 3 | Non-conflicting writes to different keys (`key0`–`key4`) | 5 | 15 |

Each experiment prints per-replica final store and delivery order, then reports **PASS** or **FAIL**. All replicas must have identical final state and identical delivery sequence.

## Network Simulator (`driver.py`)

- **`NetworkSimulator`** – Discrete-event engine. Messages are scheduled with a random delay in `[min_delay, max_delay]`. FIFO ordering per `(sender, receiver)` channel is enforced via `_channel_ready` tracking.
- **`ReplicaProxy`** – Placed in each replica's `.replicas` dict. Intercepts `handle_TOBCAST` and `handle_ACK` and routes them through the simulator so every message incurs a delay.
- **`build_network(n, sim)`** – Creates `n` replicas and wires each one's `.replicas` with proxy objects.
- **`verify(replicas)`** – Checks identical final store and delivery order across all replicas; prints per-replica report.
