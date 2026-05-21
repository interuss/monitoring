from implicitdict import ImplicitDict, Optional


class TestV1(ImplicitDict):
    namespace: str = "test"


class Test(ImplicitDict):
    v1: Optional[TestV1]
