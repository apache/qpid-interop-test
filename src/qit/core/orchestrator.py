#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#

"""
Test orchestration engine.

Coordinates shim execution, message comparison, and result reporting.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from itertools import product
from typing import Any

from qit.core.broker import BrokerManager
from qit.core.comparison import MessageComparator, MessageDiff
from qit.core.shim import Shim
from qit.core.xfail import KnownFailure, find_known_failure, get_applicable_failures


@dataclass
class TestCase:
    """Represents a single interoperability test case."""

    sender_shim: str
    receiver_shim: str
    amqp_type: str
    test_values: list[Any]


@dataclass
class TestResult:
    """Result of a test case execution."""

    test_case: TestCase
    success: bool
    diffs: list[MessageDiff]
    error: str | None = None
    duration_ms: float = 0.0
    xfail_diffs: list[tuple[MessageDiff, KnownFailure]] | None = None
    xpass_entries: list[KnownFailure] | None = None


class Orchestrator:
    """Orchestrates interoperability tests across shims."""

    def __init__(
        self,
        shims: dict[str, Shim],
        broker: BrokerManager | None = None,
    ) -> None:
        self.shims = shims
        self.broker = broker
        self.comparator = MessageComparator()

    def run_test_matrix(
        self,
        amqp_types: dict[str, list[Any]],
        sender_shims: list[str] | None = None,
        receiver_shims: list[str] | None = None,
        workers: int = 1,
    ) -> list[TestResult]:
        """
        Run full test matrix: all sender × receiver × type combinations.

        Args:
            amqp_types: Map of type name to list of test values
            sender_shims: List of sender shim names (default: all shims)
            receiver_shims: List of receiver shim names (default: all shims)
            workers: Number of parallel workers (1 = sequential)

        Returns:
            List of test results
        """
        # Default to all available shims
        sender_names = sender_shims or list(self.shims.keys())
        receiver_names = receiver_shims or list(self.shims.keys())

        # Generate test cases
        test_cases: list[TestCase] = []
        for sender, receiver, (type_name, values) in product(
            sender_names,
            receiver_names,
            amqp_types.items(),
        ):
            test_cases.append(
                TestCase(
                    sender_shim=sender,
                    receiver_shim=receiver,
                    amqp_type=type_name,
                    test_values=values,
                )
            )

        total = len(test_cases)
        print(f"Running {total} test cases (workers={workers})...")
        print(f"  Senders: {', '.join(sender_names)}")
        print(f"  Receivers: {', '.join(receiver_names)}")
        print(f"  Types: {', '.join(amqp_types.keys())}")
        print()

        if workers <= 1:
            return self._run_sequential(test_cases)
        return self._run_parallel(test_cases, workers)

    def _run_sequential(self, test_cases: list[TestCase]) -> list[TestResult]:
        results: list[TestResult] = []
        total = len(test_cases)
        for i, test_case in enumerate(test_cases, 1):
            print(f"[{i}/{total}] Testing {test_case.sender_shim} → {test_case.receiver_shim} "
                  f"({test_case.amqp_type})...", end=" ", flush=True)

            result = self.run_test_case(test_case)
            results.append(result)
            self._print_result(result)

        return results

    def _run_parallel(self, test_cases: list[TestCase], workers: int) -> list[TestResult]:
        import threading

        total = len(test_cases)
        completed = 0
        failed = 0
        lock = threading.Lock()
        result_map: dict[int, TestResult] = {}

        def run_one(index: int, tc: TestCase) -> tuple[int, TestResult]:
            return index, self.run_test_case(tc)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(run_one, i, tc): i
                for i, tc in enumerate(test_cases)
            }
            for future in as_completed(futures):
                index, result = future.result()
                result_map[index] = result
                with lock:
                    completed += 1
                    if not result.success:
                        failed += 1
                    tc = test_cases[index]
                    status = self._result_symbol(result)
                    print(f"[{completed}/{total}] {tc.sender_shim} → {tc.receiver_shim} "
                          f"({tc.amqp_type}) {status}", flush=True)

        results = [result_map[i] for i in range(total)]

        if failed:
            print(f"\nFailed tests:")
            for i, result in enumerate(results):
                if not result.success:
                    tc = test_cases[i]
                    print(f"  {tc.sender_shim} → {tc.receiver_shim} ({tc.amqp_type})")
                    if result.error:
                        print(f"    Error: {result.error}")
                    if result.diffs:
                        print(f"    {len(result.diffs)} difference(s) found")

        return results

    @staticmethod
    def _result_symbol(result: "TestResult") -> str:
        if result.success and not result.xfail_diffs:
            return "✓"
        if result.success and result.xfail_diffs:
            return f"✓ ({len(result.xfail_diffs)} xfail)"
        return "✗"

    @staticmethod
    def _print_result(result: "TestResult") -> None:
        if result.success and not result.xfail_diffs:
            print("✓")
        elif result.success and result.xfail_diffs:
            print(f"✓ ({len(result.xfail_diffs)} xfail)")
        else:
            print("✗")
            if result.error:
                print(f"  Error: {result.error}")
            if result.diffs:
                print(f"  {len(result.diffs)} difference(s) found")

    def run_test_case(self, test_case: TestCase) -> TestResult:
        """
        Run a single test case.

        Args:
            test_case: Test case to execute

        Returns:
            Test result
        """
        import time

        start_time = time.time()

        try:
            # Get shims
            sender = self.shims.get(test_case.sender_shim)
            receiver = self.shims.get(test_case.receiver_shim)

            if not sender:
                return TestResult(
                    test_case=test_case,
                    success=False,
                    diffs=[],
                    error=f"Sender shim not found: {test_case.sender_shim}",
                )

            if not receiver:
                return TestResult(
                    test_case=test_case,
                    success=False,
                    diffs=[],
                    error=f"Receiver shim not found: {test_case.receiver_shim}",
                )

            # Ensure broker is available
            if self.broker is None:
                return TestResult(
                    test_case=test_case,
                    success=False,
                    diffs=[],
                    error="No broker configured (use --mode direct for broker-less tests)",
                )

            # Generate unique queue name for this test
            queue_name = f"qit.test.{test_case.amqp_type}.{test_case.sender_shim}.{test_case.receiver_shim}"

            # Send messages
            send_result = sender.send(
                broker_url=self.broker.config.url,
                queue_name=queue_name,
                amqp_type=test_case.amqp_type,
                values=test_case.test_values,
            )

            if not send_result.success:
                duration_ms = (time.time() - start_time) * 1000
                applicable = get_applicable_failures(
                    test_case.sender_shim,
                    test_case.receiver_shim,
                    test_case.amqp_type,
                )
                if applicable:
                    return TestResult(
                        test_case=test_case,
                        success=True,
                        diffs=[],
                        error=f"Send failed (xfail): {send_result.error}",
                        duration_ms=duration_ms,
                        xfail_diffs=[(
                            MessageDiff(index=-1, field="error",
                                        expected="success", actual="send_error",
                                        message=f"Send error: {send_result.error}"),
                            applicable[0],
                        )],
                    )
                return TestResult(
                    test_case=test_case,
                    success=False,
                    diffs=[],
                    error=f"Send failed: {send_result.error}",
                    duration_ms=duration_ms,
                )

            # Receive messages
            recv_result = receiver.receive(
                broker_url=self.broker.config.url,
                queue_name=queue_name,
                count=len(test_case.test_values),
                timeout=5,  # 5 second timeout - messages should arrive quickly
            )

            if not recv_result.success:
                return TestResult(
                    test_case=test_case,
                    success=False,
                    diffs=[],
                    error=f"Receive failed: {recv_result.error}",
                )

            # Compare messages
            all_diffs = self.comparator.compare_messages(
                send_result.messages,
                recv_result.messages,
            )

            duration_ms = (time.time() - start_time) * 1000

            # Classify diffs into genuine failures vs expected failures
            genuine, xfail_diffs, xpass = self._classify_diffs(
                test_case, all_diffs,
            )

            return TestResult(
                test_case=test_case,
                success=len(genuine) == 0,
                diffs=genuine,
                duration_ms=duration_ms,
                xfail_diffs=xfail_diffs,
                xpass_entries=xpass,
            )

        except Exception as e:
            return TestResult(
                test_case=test_case,
                success=False,
                diffs=[],
                error=f"Unexpected error: {e}",
            )

    def _classify_diffs(
        self,
        test_case: TestCase,
        diffs: list[MessageDiff],
    ) -> tuple[list[MessageDiff], list[tuple[MessageDiff, KnownFailure]], list[KnownFailure]]:
        """Partition diffs into genuine failures and expected failures.

        Returns:
            (genuine_diffs, xfail_diffs, xpass_entries)
        """
        genuine: list[MessageDiff] = []
        xfail_diffs: list[tuple[MessageDiff, KnownFailure]] = []
        matched_indices: set[int] = set()

        for diff in diffs:
            kf = find_known_failure(
                test_case.sender_shim,
                test_case.receiver_shim,
                test_case.amqp_type,
                diff.index,
            )
            if kf is not None:
                xfail_diffs.append((diff, kf))
                matched_indices.add(diff.index)
            else:
                genuine.append(diff)

        # Find xpass: registered failures that didn't produce any diffs
        xpass: list[KnownFailure] = []
        applicable = get_applicable_failures(
            test_case.sender_shim,
            test_case.receiver_shim,
            test_case.amqp_type,
        )
        for kf in applicable:
            if kf.message_indices is not None:
                if not kf.message_indices & matched_indices:
                    xpass.append(kf)
            elif not matched_indices:
                xpass.append(kf)

        return genuine, xfail_diffs, xpass

    def generate_report(self, results: list[TestResult]) -> str:
        """Generate a summary report of test results."""
        total = len(results)
        passed = sum(1 for r in results if r.success and not r.xfail_diffs)
        failed = sum(1 for r in results if not r.success)
        xfail_count = sum(1 for r in results if r.success and r.xfail_diffs)
        xpass_count = sum(1 for r in results if r.xpass_entries)

        lines = [
            "=" * 80,
            "Test Results Summary",
            "=" * 80,
            f"Total:  {total}",
            f"Passed: {passed} ({100 * passed / total:.1f}%)" if total > 0 else "Passed: 0",
            f"Failed: {failed}",
        ]
        if xfail_count > 0:
            lines.append(f"XFail:  {xfail_count} (known issues)")
        if xpass_count > 0:
            lines.append(f"XPass:  {xpass_count} (known issues that now pass)")
        lines.append("")

        if failed > 0:
            lines.append("Failed Tests:")
            lines.append("-" * 80)
            for result in results:
                if not result.success:
                    tc = result.test_case
                    lines.append(f"  {tc.sender_shim} → {tc.receiver_shim} ({tc.amqp_type})")
                    if result.error:
                        lines.append(f"    Error: {result.error}")
                    if result.diffs:
                        for diff in result.diffs[:3]:
                            lines.append(f"    {diff.message}")
                        if len(result.diffs) > 3:
                            lines.append(f"    ... and {len(result.diffs) - 3} more")
                    lines.append("")

        if xfail_count > 0:
            lines.append("Expected Failures (known issues):")
            lines.append("-" * 80)
            for result in results:
                if result.success and result.xfail_diffs:
                    tc = result.test_case
                    reasons = {kf.reason for _, kf in result.xfail_diffs}
                    lines.append(
                        f"  {tc.sender_shim} → {tc.receiver_shim} ({tc.amqp_type}): "
                        f"{len(result.xfail_diffs)} diff(s)"
                    )
                    for reason in sorted(reasons):
                        lines.append(f"    [XFAIL] {reason}")
            lines.append("")

        if xpass_count > 0:
            lines.append("Unexpected Passes (investigate — known issues now passing):")
            lines.append("-" * 80)
            for result in results:
                if result.xpass_entries:
                    tc = result.test_case
                    for kf in result.xpass_entries:
                        lines.append(
                            f"  {tc.sender_shim} → {tc.receiver_shim} ({tc.amqp_type}): "
                            f"[XPASS] {kf.reason}"
                        )
            lines.append("")

        lines.append("=" * 80)
        return "\n".join(lines)

    def generate_junit_xml(
        self,
        results: list[TestResult],
        output_path: str,
        strict: bool = False,
    ) -> None:
        """
        Generate JUnit XML report for CI/CD integration.

        Args:
            results: Test results to report
            output_path: Path to write XML file
            strict: If True, xfails are reported as failures
        """
        from pathlib import Path
        from xml.etree.ElementTree import Element, SubElement, tostring
        from xml.dom import minidom

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        total = len(results)
        failed = sum(1 for r in results if not r.success)
        skipped = sum(1 for r in results if r.success and r.xfail_diffs)
        if strict:
            failed += skipped
            skipped = 0
        total_time_sec = sum(r.duration_ms for r in results) / 1000

        testsuite = Element(
            "testsuite",
            name="QIT AMQP Interoperability Tests",
            tests=str(total),
            failures=str(failed),
            errors="0",
            skipped=str(skipped),
            time=f"{total_time_sec:.3f}",
        )

        for result in results:
            tc = result.test_case
            testcase = SubElement(
                testsuite,
                "testcase",
                classname=f"qit.{tc.sender_shim}.{tc.receiver_shim}",
                name=f"{tc.amqp_type}",
                time=f"{result.duration_ms / 1000:.3f}",
            )

            if not result.success:
                failure_msg = result.error if result.error else f"{len(result.diffs)} message difference(s)"
                failure_details = []

                if result.error:
                    failure_details.append(f"Error: {result.error}")

                if result.diffs:
                    failure_details.append(f"\nMessage Differences ({len(result.diffs)} total):")
                    for diff in result.diffs[:10]:
                        failure_details.append(f"  - {diff.message}")
                    if len(result.diffs) > 10:
                        failure_details.append(f"  ... and {len(result.diffs) - 10} more differences")

                failure = SubElement(
                    testcase,
                    "failure",
                    message=failure_msg,
                    type="InteroperabilityFailure",
                )
                failure.text = "\n".join(failure_details)

            elif result.xfail_diffs:
                if strict:
                    reasons = {kf.reason for _, kf in result.xfail_diffs}
                    failure = SubElement(
                        testcase,
                        "failure",
                        message=f"{len(result.xfail_diffs)} known issue(s) (strict mode)",
                        type="KnownIssue",
                    )
                    failure.text = "\n".join(
                        f"  - {reason}" for reason in sorted(reasons)
                    )
                else:
                    reasons = {kf.reason for _, kf in result.xfail_diffs}
                    skipped_elem = SubElement(
                        testcase,
                        "skipped",
                        message=f"Known: {'; '.join(sorted(reasons))}",
                    )

            if result.xpass_entries:
                sysout = SubElement(testcase, "system-out")
                xpass_lines = [
                    f"[XPASS] {kf.reason}" for kf in result.xpass_entries
                ]
                sysout.text = "\n".join(xpass_lines)

        xml_str = minidom.parseString(tostring(testsuite, encoding="unicode")).toprettyxml(indent="  ")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(xml_str)
