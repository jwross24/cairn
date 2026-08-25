from cairn import exits


class CliError(Exception):
    def __init__(self, code, what, *, where=None, next_command=None):
        super().__init__(what)
        self.code = code
        self.what = what
        self.where = where
        self.next_command = next_command

    def record(self):
        return {
            "code": self.code,
            "meaning": exits.CLI.get(self.code, "?"),
            "what": self.what,
            "where": self.where,
            "next_command": self.next_command,
        }

    def human(self):
        parts = [f"error: {self.what}"]
        if self.where:
            parts.append(f"({self.where})")
        line = " ".join(parts)
        if self.next_command:
            line += f"; run: {self.next_command}"
        return line
