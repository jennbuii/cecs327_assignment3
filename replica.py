from messages import TOBCAST, ACK

class Replica:
    def __init__(self, replica_id, every_replica_id):
        self.k = replica_id  # each replica has a unique id
        self.Rk = every_replica_id  # list of all replica ids

        self.clock_i = 0
        self.holdback_queue = []
        self.max_seen = {rid: -1 for rid in self.Rk} # progress tracking
        self.store = {} #key-value replicated store
        self.replicas = {} # mapping from replica id to replica object
        self.delivered_log = [] # ordered list of update_ids in delivery order

    def apply_operation(self, op):
        if op["op"] == "put": # put(k,v)
            self.store[op["key"]] = op["val"]
        elif op["op"] == "append": # append(k, suffix)
            if op["key"] not in self.store:
                self.store[op["key"]] = ""
            self.store[op["key"]] = self.store[op["key"]] + str(op["val"])
        elif op["op"] == "incr": # incr(k)
            if op["key"] not in self.store:
                self.store[op["key"]] = 0   
            self.store[op["key"]] += 1

    def deliver(self):
        while self.holdback_queue:
            m = self.holdback_queue[0]
            m_ts = m["ts"][0]
            can_deliver = True

            for rid in self.Rk:
                if not(self.max_seen[rid] > m_ts): # progress tracking
                    can_deliver = False
                    break
            if can_deliver:
                self.holdback_queue.pop(0)
                self.apply_operation(m["op"])
                self.delivered_log.append(m["update_id"])
            else:
                break

    def handle_ACK(self, m):
        self.clock_i = max(self.clock_i, m["ts"][0]) + 1
        self.max_seen[m["sender_id"]] = max(self.max_seen[m["sender_id"]], m["ts"][0])
        self.deliver()

    def handle_TOBCAST(self, m):
        self.clock_i = max(self.clock_i, m["ts"][0]) + 1
        self.holdback_queue.append(m)
        self.holdback_queue.sort(key=lambda m: m["ts"])
        self.max_seen[m["sender_id"]] = max(self.max_seen[m["sender_id"]], m["ts"][0]) # largest time stamp seen from sender_id

        self.clock_i += 1
        ts = (self.clock_i, self.k)
        ack = ACK(m["update_id"], ts, self.k)
        for rid in self.replicas:
            self.replicas[rid].handle_ACK(ack)
        self.deliver()  # handles case where ACKs arrived before this TOBCAST

    def handle_request(self, op):
        self.clock_i += 1 # increments Lamport clock before sending TOBCAST
        ts = (self.clock_i, self.k)
        update_id = (self.k, self.clock_i) # message identified by the sender and the time sent
        m = TOBCAST(update_id, op, ts, self.k)
        for rid in self.replicas:
            self.replicas[rid].handle_TOBCAST(m)
        