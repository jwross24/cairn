class SubstrateError(Exception):
    pass


class HashCollision(SubstrateError):
    pass


class HashMismatch(SubstrateError):
    pass


class GradeError(SubstrateError):
    pass


class UnknownNode(SubstrateError):
    pass


class UnknownAttempt(SubstrateError):
    pass


class WriterAlreadyOpen(SubstrateError):
    pass


class SchemaMismatch(SubstrateError):
    pass


class NeedsMigration(SchemaMismatch):
    pass
