"""Global, parameterizable settings for a benchmark run."""

from dataclasses import dataclass


@dataclass
class GlobalConfig:
    # Local ecosystem sizing (consumed by `make start-locally`).
    num_uss: int = 3
    num_nodes: int = 3
    dss_image: str = "interuss/dss:v0.22.0"
    db_type: str = "crdb"  # crdb | ybdb | raft
    intra_netem: str = "delay 600us 40us 25% distribution normal loss 0.0005%"
    inter_netem: str = "delay 36ms 40ms 50% distribution paretonormal loss 0.25% 15%"

    # Load profile.
    duration_s: float = 120.0
    processes: int = 4  # parallel processes calling action(), PER DSS

    # Dummy OAuth reachable from the host.
    oauth_token_endpoint: str = "http://localhost:8085/token"
    oauth_sub: str = "uss1"
