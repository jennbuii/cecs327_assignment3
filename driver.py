import heapq
import random
from replica import Replica
from messages import oper

class NetworkSimulator:
    def __init__(self, min_delay: float = 0.01, max_delay: float = 0.5,
                 seed: int = None):
        self.current_time: float = 0.0
        self._queue: list = []  # min-heap: (delivery_time, seq, func, args)
        self._seq: int = 0      # tiebreaker so heap never compares functions
        self.min_delay = min_delay
        self.max_delay = max_delay
        self._channel_ready: dict = {}   # (src, dst) -> earliest next delivery time
        self.event_count: int = 0
        if seed is not None:
            random.seed(seed)

    def schedule(self, src_id, dst_id, func, *args):
        key = (src_id, dst_id)
        # FIFO: cannot arrive before previous message on channel
        earliest = max(self.current_time, self._channel_ready.get(key, 0.0))
        delay = random.uniform(self.min_delay, self.max_delay)
        delivery_time = earliest + delay
        self._channel_ready[key] = delivery_time   # next message on channel >= this time
        heapq.heappush(self._queue, (delivery_time, self._seq, func, args))
        self._seq += 1

    def run(self):
        # Process all queued delivery events in delivery time order.
        while self._queue:
            t, _, func, args = heapq.heappop(self._queue)
            self.current_time = t
            self.event_count += 1
            func(*args)

# Replica Proxy
class ReplicaProxy:
    def __init__(self, real_replica: Replica, sender_id, sim: NetworkSimulator):
        self.real_replica = real_replica
        self.sender_id = sender_id
        self.sim = sim
        self.k = real_replica.k   # expose .k so replica works

    def handle_TOBCAST(self, m):
        self.sim.schedule(self.sender_id, self.real_replica.k,
                          self.real_replica.handle_TOBCAST, m)

    def handle_ACK(self, m):
        self.sim.schedule(self.sender_id, self.real_replica.k,
                          self.real_replica.handle_ACK, m)

# Factory
def build_network(n: int, sim: NetworkSimulator) -> dict:
    ids = list(range(n))
    replicas = {i: Replica(i, ids) for i in ids}
    for src_id, src_rep in replicas.items():
        src_rep.replicas = {
            dst_id: ReplicaProxy(replicas[dst_id], src_id, sim)
            for dst_id in ids
        }
    return replicas

# Verify
def verify(replicas: dict) -> bool:
    stores = [rep.store        for rep in replicas.values()]
    logs   = [rep.delivered_log for rep in replicas.values()]

    store_ok = all(s == stores[0] for s in stores)
    log_ok   = all(l == logs[0]   for l in logs)

    for rid, rep in replicas.items():
        delivered_str = ", ".join(str(uid) for uid in rep.delivered_log)
        print(f"R{rid} store={rep.store}")
        print(f"   log=[{delivered_str}]")

    if store_ok and log_ok:
        print("PASS – all replicas converged")
    else:
        if not store_ok:
            print("FAIL – stores differ")
        if not log_ok:
            print("FAIL – delivery orders differ")

    return store_ok and log_ok

# Experiment 1: Concurrent Conflicting Updates
def experiment1() -> bool:
    print("Experiment 1: Concurrent Conflicting Updates (3 replicas)")

    sim = NetworkSimulator(max_delay=0.3, seed=42)
    reps = build_network(3, sim)

    submissions = [
        (0, oper("put",    "x", "100")),
        (1, oper("append", "x", "_extra")),
        (2, oper("put",    "x", "999")),
    ]
    for rid, op in submissions:
        val_str = repr(op["val"]) if op["val"] is not None else ""
        print(f"  client -> R{rid}: {op['op']}({op['key']!r}, {val_str})")
        reps[rid].handle_request(op)

    sim.run()
    return verify(reps)


# Experiment 2: High Contention
def experiment2(n_updates: int = 30, n_replicas: int = 4) -> bool:
    print(f"Experiment 2: High Contention ({n_updates} updates, {n_replicas} replicas)")

    sim = NetworkSimulator(max_delay=0.5, seed=7)
    reps = build_network(n_replicas, sim)

    for i in range(n_updates):
        reps[i % n_replicas].handle_request(oper("incr", "counter"))

    sim.run()
    ok = verify(reps)

    for rid, rep in reps.items():
        got = rep.store.get("counter", None)
        if got != n_updates:
            print(f"COUNTER MISMATCH at R{rid}: expected {n_updates}, got {got}")
            ok = False

    return ok


# Experiment 3: Non-Conflicting Updates
def experiment3() -> bool:
    print("Experiment 3: Non-Conflicting Updates (5 replicas, 5 keys)")

    sim = NetworkSimulator(max_delay=0.4, seed=123)
    reps = build_network(5, sim)
    n = len(reps)

    accounts = [f"key{i}" for i in range(5)]

    for i, acc in enumerate(accounts):
        reps[i % n].handle_request(oper("put", acc, 1000))

    for i, acc in enumerate(accounts):
        reps[i % n].handle_request(oper("incr", acc))
        reps[(i + 2) % n].handle_request(oper("incr", acc))

    sim.run()
    return verify(reps)


# Entry Point
if __name__ == "__main__":
    r1 = experiment1()
    print()
    r2 = experiment2(n_updates=30)
    print()
    r3 = experiment3()
    results = [r1, r2, r3]
    print("\nSummary:")
    for i, ok in enumerate(results, 1):
        print(f"  Experiment {i}: {'PASS' if ok else 'FAIL'}")
    print(f"  Overall: {'ALL PASSED' if all(results) else 'SOME FAILED'}")
