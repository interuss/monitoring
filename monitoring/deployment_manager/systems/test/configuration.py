from implicitdict import ImplicitDict


class TestV1(ImplicitDict):
    namespace: str = "test"


class Test(ImplicitDict):
    v1: TestV1 | None
