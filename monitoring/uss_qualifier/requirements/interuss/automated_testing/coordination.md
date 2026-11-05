# InterUSS automated test coordination requirements

## Requirements

### <tt>AccessSharedAssets</tt>

When a test configuration designer uses a coordinator that coordinates exclusive access to shared assets, a request to gain access to a shared asset must succeed within the allowed acquisition parameters (e.g., time limit).  A test configuration designer can often reduce violation of this requirement by extending the acceptable time taken to acquire exclusive access to the shared asset.
