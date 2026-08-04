"""
Known failure registry for expected test failures.

Tracks client library limitations and known bugs that should not block CI.
Each entry documents the specific failure, its root cause, and optionally
a link to the upstream bug tracker.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class KnownFailure:
    """A known test failure caused by a client library limitation."""

    sender: str
    receiver: str
    amqp_type: str
    message_indices: frozenset[int] | None
    reason: str
    bug_url: str = ""


def find_known_failure(
    sender: str,
    receiver: str,
    amqp_type: str,
    message_index: int,
) -> KnownFailure | None:
    """Find a matching known failure entry for a specific test diff.

    Returns the first matching KnownFailure, or None if no match.
    """
    for kf in KNOWN_FAILURES:
        if kf.amqp_type != amqp_type:
            continue
        if kf.sender != "*" and kf.sender != sender:
            continue
        if kf.receiver != "*" and kf.receiver != receiver:
            continue
        if kf.message_indices is not None and message_index not in kf.message_indices:
            continue
        return kf
    return None


def get_applicable_failures(
    sender: str,
    receiver: str,
    amqp_type: str,
) -> list[KnownFailure]:
    """Get all known failures that apply to a given test case."""
    result = []
    for kf in KNOWN_FAILURES:
        if kf.amqp_type != amqp_type:
            continue
        if kf.sender != "*" and kf.sender != sender:
            continue
        if kf.receiver != "*" and kf.receiver != receiver:
            continue
        result.append(kf)
    return result


# ---------------------------------------------------------------------------
# Registry of known failures
#
# Each entry documents a client library limitation that causes predictable
# test failures. These are NOT QIT bugs — they are upstream issues.
# ---------------------------------------------------------------------------

KNOWN_FAILURES: list[KnownFailure] = [
    # --- JavaScript Rhea: parseInt() precision loss for values > 2^53 ---
    KnownFailure(
        sender="javascript-rhea", receiver="*", amqp_type="ulong",
        message_indices=frozenset({6, 7, 8, 9}),
        reason="JS number precision loss for ulong values > 2^53",
    ),
    KnownFailure(
        sender="*", receiver="javascript-rhea", amqp_type="ulong",
        message_indices=frozenset({6, 7, 8, 9}),
        reason="JS number precision loss for ulong values > 2^53",
    ),
    KnownFailure(
        sender="javascript-rhea", receiver="*", amqp_type="long",
        message_indices=frozenset({0, 3, 13, 14}),
        reason="JS number precision loss for long values with |v| > 2^53",
    ),
    KnownFailure(
        sender="*", receiver="javascript-rhea", amqp_type="long",
        message_indices=frozenset({0, 3, 13, 14}),
        reason="JS number precision loss for long values with |v| > 2^53",
    ),

    # --- Java ProtonJ2: 16-bit char truncates supplementary codepoints ---
    KnownFailure(
        sender="java-protonj2", receiver="*", amqp_type="char",
        message_indices=frozenset({8}),
        reason="Java char is 16-bit, truncates codepoints > U+FFFF",
    ),
    KnownFailure(
        sender="*", receiver="java-protonj2", amqp_type="char",
        message_indices=frozenset({8}),
        reason="Java char is 16-bit, truncates codepoints > U+FFFF",
    ),

    # --- .NET Proton: 16-bit char truncates supplementary codepoints ---
    KnownFailure(
        sender="dotnet-proton", receiver="*", amqp_type="char",
        message_indices=frozenset({8}),
        reason=".NET char is 16-bit, truncates codepoints > U+FFFF",
    ),
    KnownFailure(
        sender="*", receiver="dotnet-proton", amqp_type="char",
        message_indices=frozenset({8}),
        reason=".NET char is 16-bit, truncates codepoints > U+FFFF",
    ),

    # --- .NET Proton: byte[]/binary ambiguity in lists ---
    # byte[] implements IList<byte>, so Proton .NET encodes it as AMQP
    # array-of-ubyte instead of binary when it appears inside a list.
    KnownFailure(
        sender="dotnet-proton", receiver="*", amqp_type="list",
        message_indices=frozenset({3, 8}),
        reason="Proton .NET encodes byte[] as array-of-ubyte in lists",
    ),

    # --- .NET Proton: timestamp decoded as Int64 in lists ---
    KnownFailure(
        sender="*", receiver="dotnet-proton", amqp_type="list",
        message_indices=frozenset({3, 8}),
        reason="Proton .NET decodes timestamp as Int64 in list context",
    ),

    # --- .NET Proton: ListTypeEncoder NRE with null after non-null ---
    KnownFailure(
        sender="dotnet-proton", receiver="*", amqp_type="list",
        message_indices=frozenset({7}),
        reason="Proton .NET ListTypeEncoder NullReferenceException: null after non-null",
    ),

    # --- Java ProtonJ2: ListTypeEncoder NRE with null after non-null ---
    KnownFailure(
        sender="java-protonj2", receiver="*", amqp_type="list",
        message_indices=frozenset({7}),
        reason="ProtonJ2 ListTypeEncoder NullPointerException: null after non-null",
    ),

    # --- Java ProtonJ2: unsigned long values > Long.MAX_VALUE ---
    KnownFailure(
        sender="*", receiver="java-protonj2", amqp_type="ulong",
        message_indices=frozenset({8, 9}),
        reason="ProtonJ2 decodes unsigned long values > 2^63 as negative signed long",
    ),

    # --- .NET Proton: ubyte arrays decoded as binary ---
    KnownFailure(
        sender="*", receiver="dotnet-proton", amqp_type="array",
        message_indices=frozenset({7}),
        reason="Proton .NET byte[]/binary ambiguity for nested ubyte arrays",
    ),

    # --- Java ProtonJ2: binary/timestamp decoded incorrectly in lists ---
    KnownFailure(
        sender="*", receiver="java-protonj2", amqp_type="list",
        message_indices=frozenset({3, 8}),
        reason="ProtonJ2 decodes binary/timestamp incorrectly in list context",
    ),

    # --- Java ProtonJ2: null character (U+0000) encoding ---
    KnownFailure(
        sender="java-protonj2", receiver="*", amqp_type="char",
        message_indices=frozenset({0}),
        reason="ProtonJ2 encodes null character (U+0000) incorrectly",
    ),

    # --- .NET Proton: empty binary round-trip ---
    KnownFailure(
        sender="dotnet-proton", receiver="dotnet-proton", amqp_type="binary",
        message_indices=frozenset({0}),
        reason="Proton .NET empty binary round-trip type mismatch",
    ),

    # --- .NET Proton → Java ProtonJ2: binary encoding incompatibility ---
    KnownFailure(
        sender="dotnet-proton", receiver="java-protonj2", amqp_type="binary",
        message_indices=None,
        reason="Proton .NET binary encoding incompatible with ProtonJ2 binary decoder",
    ),

    # --- .NET Proton: timestamp decoded as Int64 (primitive type) ---
    KnownFailure(
        sender="*", receiver="dotnet-proton", amqp_type="timestamp",
        message_indices=None,
        reason="Proton .NET decodes timestamp as Int64 instead of DateTime",
    ),

    # --- Java ProtonJ2: timestamp decoded as Long (primitive type) ---
    KnownFailure(
        sender="*", receiver="java-protonj2", amqp_type="timestamp",
        message_indices=None,
        reason="ProtonJ2 decodes timestamp as Long instead of Date",
    ),
]
