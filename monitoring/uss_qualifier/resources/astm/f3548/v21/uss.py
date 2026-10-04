from dataclasses import dataclass

from monitoring.monitorlib.infrastructure import UTMClientSession


@dataclass(frozen=True)
class USSInstance:
    participant_id: str
    """Participant responsible for this USS instance"""

    base_url: str
    """Base URL for the USS instance according to the ASTM F3548-21 API"""

    client: UTMClientSession
    """Requests session that enables easy access to ASTM-specified UTM endpoints"""
