from dataclasses import dataclass


class Specification:
    def is_satisfied_by(self, candidate):
        raise NotImplementedError

    def __and__(self, other):
        return Composite(self, other, "AND")

    def __or__(self, other):
        return Composite(self, other, "OR")

    def __invert__(self):
        return Negated(self)


@dataclass(frozen=True)
class Composite(Specification):
    left: Specification
    right: Specification
    operation: str

    def is_satisfied_by(self, candidate):
        if self.operation == "AND":
            return self.left.is_satisfied_by(candidate) and self.right.is_satisfied_by(candidate)
        return self.left.is_satisfied_by(candidate) or self.right.is_satisfied_by(candidate)


@dataclass(frozen=True)
class Negated(Specification):
    inner: Specification

    def is_satisfied_by(self, candidate):
        return not self.inner.is_satisfied_by(candidate)


class ActiveClient(Specification):
    def is_satisfied_by(self, candidate):
        return candidate["active"]


class HasLines(Specification):
    def is_satisfied_by(self, candidate):
        return bool(candidate["lines"])


class Authorized(Specification):
    def is_satisfied_by(self, candidate):
        return candidate["authorized"]


class PendingBalance(Specification):
    def is_satisfied_by(self, candidate):
        return candidate["balance"] > 0


class MissingInformation(Specification):
    def is_satisfied_by(self, candidate):
        return not candidate["complete"]


# AND/OR/NOT participan en reglas reales del BRD.
CAN_SEND = ActiveClient() & HasLines() & Authorized()
CAN_CLOSE = ~(PendingBalance() | MissingInformation())
