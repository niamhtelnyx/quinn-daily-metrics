"""Custom exception hierarchy for the A2A client.

This module defines a structured exception hierarchy for handling errors
that can occur when communicating with A2A protocol agents.
"""


class A2AClientError(Exception):
    """Base exception for all A2A client errors."""


class A2AConnectionError(A2AClientError):
    """Raised when a connection to the A2A agent fails."""

    def __init__(self, message: str, url: str | None = None):
        self.url = url
        super().__init__(f"Connection failed{f' to {url}' if url else ''}: {message}")


class A2ATimeoutError(A2AClientError):
    """Raised when an A2A operation times out."""

    def __init__(self, message: str, timeout_seconds: float | None = None):
        self.timeout_seconds = timeout_seconds
        timeout_info = f" after {timeout_seconds}s" if timeout_seconds else ""
        super().__init__(f"Operation timed out{timeout_info}: {message}")


class A2AAuthenticationError(A2AClientError):
    """Raised when authentication with the A2A agent fails."""

    def __init__(self, message: str, status_code: int | None = None):
        self.status_code = status_code
        super().__init__(f"Authentication failed: {message}")


class A2AProtocolError(A2AClientError):
    """Raised when there is a protocol-level error in A2A communication."""

    def __init__(self, message: str, error_code: int | None = None):
        self.error_code = error_code
        code_info = f" (code: {error_code})" if error_code else ""
        super().__init__(f"Protocol error{code_info}: {message}")


class A2ATaskError(A2AClientError):
    """Base exception for task-related errors."""

    def __init__(self, message: str, task_id: str | None = None):
        self.task_id = task_id
        task_info = f" [task: {task_id}]" if task_id else ""
        super().__init__(f"Task error{task_info}: {message}")


class A2ATaskNotFoundError(A2ATaskError):
    """Raised when a requested task is not found."""

    def __init__(self, task_id: str):
        super().__init__(f"Task not found: {task_id}", task_id=task_id)


class A2ATaskFailedError(A2ATaskError):
    """Raised when a task fails during execution."""

    def __init__(self, message: str, task_id: str | None = None):
        super().__init__(f"Task failed: {message}", task_id=task_id)


class A2ATaskCanceledError(A2ATaskError):
    """Raised when a task is canceled."""

    def __init__(self, task_id: str):
        super().__init__(f"Task was canceled: {task_id}", task_id=task_id)


class A2AInputRequiredError(A2AClientError):
    """Raised when the agent requires additional input to proceed."""

    def __init__(self, message: str, task_id: str, context_id: str | None = None):
        self.task_id = task_id
        self.context_id = context_id
        self.agent_question = message
        super().__init__(f"Agent requires input: {message}")


class A2AMaxTurnsExceededError(A2AClientError):
    """Raised when the maximum number of conversation turns is exceeded."""

    def __init__(self, max_turns: int, task_id: str | None = None):
        self.max_turns = max_turns
        self.task_id = task_id
        super().__init__(f"Maximum conversation turns ({max_turns}) exceeded")
