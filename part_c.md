Q1. Why does replication need total ordering for conflicting operations? Use a concrete example.
Without total ordering, replicas can apply conflicting writes in different order and permanently split. If R0 first does put(x, "100") then put(x, "999"), and R1 does it in the reversed order then RO and R1 would end up with x="999" and x="100" resepctively. They must both write in the same order.

Q2. What do Lamport clocks guarantee and what do they not guarantee? (ordering vs real time; partial order vs total order with tie-breaks)
Lamport clocks guarentee that if A precedes B then ts(A) < ts(B). With tie breaking by replica ID they will produce the total order. They don't reflect real time and a higher timestamp does not imply a real world event. They also cannot tell concurrent events from ordered events.

Q3. Your algorithm assumes reliable FIFO communication. What breaks if messages can be lost or delivered out of FIFO order?
If a message is lost the sender advances so no later message from that sender can satisfy the delivery condition. The queue will stall indefinitely. If the delivery is not FIFO, a replica may see a later message before a previous message from the same sender causing messages to deliver out of order.

Q4. Where is the “coordination” happening in your implementation (middleware vs application logic)? 
ALl coordination is in the replica class, lamport clock updates, TOBCAST/ACK multicasing, holdback queue management, and the delivery condition. The apply_operation executes the operations as it recieves and has no knowledge of other replicas or their ordering.
