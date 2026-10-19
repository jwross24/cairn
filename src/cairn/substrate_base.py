from contextlib import contextmanager

from cairn.substrate_errors import SubstrateError


class SubstrateBase:
    def __init__(self, conn, path, role):
        self.conn = conn
        self.path = path
        self.role = role
        self.closed = False
        self._depth = 0
        self._failed = False

    @contextmanager
    def transaction(self):
        if self._depth:
            self._depth += 1
            try:
                yield
            except BaseException:
                self._failed = True
                raise
            finally:
                self._depth -= 1
            return
        self.conn.execute("BEGIN IMMEDIATE")
        self._depth, self._failed = 1, False
        try:
            yield
        except BaseException:
            self._depth, self._failed = 0, False
            self.conn.execute("ROLLBACK")
            raise
        self._depth = 0
        if self._failed:
            self._failed = False
            self.conn.execute("ROLLBACK")
            raise SubstrateError("a write in this transaction raised; the block is rolled back")
        self.conn.execute("COMMIT")

    def _tx(self):
        return self.transaction()
