# Legacy swarm client — retired

This old prototype is not a supported compute node. It used unsigned worker requests and placeholder outputs rather than real model inference, so it must not claim paid work or promise rewards. Its CLI, constructor and execution entry points fail closed instead of registering or submitting fabricated results.

For a working inference node, follow the [canonical GSTD node setup](https://gstdtoken.com/nodes) and [operator guide](https://github.com/gstdcoin/gstdbot/blob/main/docs/OPERATOR_PANEL.md). Use the signed Python/JavaScript monitor examples in the [repository README](../README.md) when building an integration; those monitors require a real executor before claiming work.

The [old installation and fleet instructions](../docs/archive/SWARM_README_2026-10-28.md) are retained for provenance only. Do not install or start this legacy prototype as a production node. A wallet/API key does not guarantee paid work, acceptance or a blockchain payout.
