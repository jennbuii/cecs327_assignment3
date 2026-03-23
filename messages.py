def oper(op, key, val = None):
    return {
        "op": op,
        "key": key,
        "val": val
    }

def TOBCAST(update_id, op, ts, sender_id):
    return {
        "type": "TOBCAST",
        "update_id": update_id,
        "op": op,
        "ts": ts,
        "sender_id": sender_id
    }

def ACK(update_id, ts, sender_id):
    return {
        "type": "ACK",
        "update_id": update_id,
        "ts": ts,
        "sender_id": sender_id
    }