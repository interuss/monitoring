# InterUSS DSS hosting requirements

While not all competent authorities will require any or all of these requirements, when they are required, these requirements can provide certain benefits like enabling experimental validation of successful pooling when DSS instances are the InterUSS DSS implementation.

* <tt>ExposeAux</tt>: The DSS implementation under test must expose the InterUSS-defined `aux` interface implemented by the InterUSS DSS implementation corresponding to the range of versions allowed by the competent authoity and respond to queries correctly according to that interface.
