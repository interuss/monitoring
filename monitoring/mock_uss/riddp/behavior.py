from implicitdict import ImplicitDict, Optional

ServiceProviderID = str


class DisplayProviderBehavior(ImplicitDict):
    always_omit_recent_paths: Optional[bool] = False
    do_not_display_flights_from: Optional[list[ServiceProviderID]] = []
