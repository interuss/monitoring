from enum import Enum


class Severity(str, Enum):
    Critical = "Critical"
    """The system under test has a critical problem that justifies the discontinuation of testing.

    This kind of issue not only makes the current test scenario unable to
    succeed, but is likely to cause spurious failures in other separate test
    scenarios as well.  This may occur, for instance, if the system was left
    dirty which is likely to prevent subsequent test scenarios to run correctly.
    This kind of issue should be rare as test scenarios should generally be
    mostly independent of each other.
    """

    High = "High"
    """The system under test has a problem that prevents the current test scenario from continuing.

    Error interrupts a test scenario but likely doesn't impact other, separate
    test scenarios.  For instance, the test step necessary to enable later test
    steps in the test scenario did not complete successfully.
    """

    Medium = "Medium"
    """The system does not meet requirements, but the current test scenario can continue.

    Further test steps will likely still result in reasonable evaluations.
    """

    Low = "Low"
    """The system meets requirements but could be improved.

    Further test steps can be executed without impact.  A test run with only
    Low-Severity issues will be considered successful.
    """

    def __eq__(self, other):
        if isinstance(other, Severity):
            other_str = other.value
        elif isinstance(other, str):
            other_str = other
        else:
            raise ValueError(f"Cannot compare Severity to {type(other)}")
        return self.value == other_str

    def __ne__(self, other):
        return not (self == other)

    def __gt__(self, other):
        if isinstance(other, Severity):
            pass
        elif isinstance(other, str):
            other = Severity(other)
        else:
            raise ValueError(f"Cannot compare Severity to {type(other)}")

        if self == Severity.Critical:
            return other != Severity.Critical
        elif self == Severity.High:
            return other == Severity.Medium or other == Severity.Low
        elif self == Severity.Medium:
            return other == Severity.Low
        elif self == Severity.Low:
            return False
        else:
            raise ValueError(f"Unknown Severity type: '{self}'")

    def __ge__(self, other):
        return self == other or self > other

    def __lt__(self, other):
        if isinstance(other, Severity):
            pass
        elif isinstance(other, str):
            other = Severity(other)
        else:
            raise ValueError(f"Cannot compare Severity to {type(other)}")
        return other > self

    def __le__(self, other):
        if isinstance(other, Severity):
            pass
        elif isinstance(other, str):
            other = Severity(other)
        else:
            raise ValueError(f"Cannot compare Severity to {type(other)}")
        return other >= self

    @property
    def symbol(self) -> str:
        return {
            Severity.Low.value: "ℹ️",
            Severity.Medium.value: "⚠️",
            Severity.High.value: "🛑",
            Severity.Critical.value: "☢",
        }.get(self.value, "�")
