from implicitdict import ImplicitDict

ServiceProviderID = str


class DisplayProviderBehavior(ImplicitDict):
    always_omit_recent_paths: bool | None = False
    do_not_display_flights_from: list[ServiceProviderID] | None = []
