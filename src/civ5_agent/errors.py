class Civ5AgentError(Exception):
    """Base class for supported domain and application-boundary errors."""


class ValidationError(Civ5AgentError, ValueError):
    """Input or persisted data violated a versioned contract."""


class ProtocolError(Civ5AgentError, ValueError):
    """A local application peer returned a rejected or malformed response."""


class TransportError(Civ5AgentError, ConnectionError):
    """A local application transport could not complete the exchange."""


class SafetyError(Civ5AgentError, RuntimeError):
    """A requested live operation failed a mandatory safety boundary."""
