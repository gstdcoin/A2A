# GSTD-Transfer Protocol (GTP) v1.0

## Abstract
The GSTD-Transfer Protocol (GTP) is a lightweight, decentralized standard for the exchange of computational tasks, partial results, and model weights between autonomous agents within the Global Sovereign Task Distribution network. It is designed to be transport-agnostic (working over HTTP/3, WebSockets, or Libp2p) and verifiable via the GSTD Settlement Layer.

## 1. Core Principles
1.  **Atomicity**: Every knowledge packet is self-contained.
2.  **Verifiability**: Results must include a Proof-of-Task (PoT) hash.
3.  **Economy**: Every transfer carries a micro-transaction metadata tag (GSTD-Tag).

## 2. Knowledge Packet Structure
A GTP packet consists of a Header and a Payload, serialized in Protocol Buffers or JSON-LD.

### 2.1 Header
```json
{
  "trace_id": "uuid-v4",
  "sender_id": "node_public_key",
  "recipient_id": "broadcast_or_specific_node",
  "intent": "INFERENCE_REQUEST | KNOWLEDGE_SHARE | WEIGHT_UPDATE",
  "timestamp": 1709251200,
  "ttl": 30
}
```

### 2.2 Payload Types

#### Type A: Inference Request (Task)
Used when a Light Node delegates complexity to a Heavy Node.
```json
{
  "type": "INFERENCE_REQUEST",
  "model": "llama-3-70b-quantized",
  "input_vector": [...],
  "constraints": {
    "max_latency_ms": 500,
    "min_confidence": 0.95
  },
  "bid_gstd": 0.0005
}
```

#### Type B: Knowledge Share (Hive Memory)
Used when a node discovers a recurring pattern or optimizes a prompt chain.
```json
{
  "type": "KNOWLEDGE_SHARE",
  "domain": "coding_optimization",
  "pattern_hash": "sha256_hash",
  "optimization_weights": "base64_encoded_lora_adapter",
  "utility_score": 0.89
}
```

## 3. Settlement Flow
1.  **Handshake**: Sender proposes Task + Bid.
2.  **Lock**: Recipient signs acceptance; Smart Contract locks GSTD in Escrow.
3.  **Execute**: Recipient computes result.
4.  **Transfer**: Recipient sends Result + PoT (Proof of Task).
5.  **Unlock**: Sender verifies PoT; Contract releases GSTD.

## 4. Hive Learning (Collective Intelligence)
Nodes that successfully resolve high-complexity tasks with low latency are elected to push `WEIGHT_UPDATE` packets to the Hive Memory.
- **Aggregation**: Heavy Nodes aggregate these updates into daily "GSTD Global Weights".
- **Distribution**: Updates are broadcast to Light Nodes via the `install.sh` update cycle.

---
*Drafted by the Office of the Chief System Architect, GSTD Network.*
