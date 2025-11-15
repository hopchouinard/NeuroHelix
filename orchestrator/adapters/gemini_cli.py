"""Gemini CLI adapter with retries and timeouts."""

import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from config.settings_schema import PromptPolicy
from services.rate_limiter import RateLimitError, get_rate_limiter


class GeminiCLIError(Exception):
    """Exception raised when Gemini CLI execution fails."""

    pass


class RateLimitDetectedError(Exception):
    """Exception raised when rate limiting is detected."""

    pass


class GeminiCLIAdapter:
    """Adapter for executing Gemini CLI commands with retry logic and rate limiting."""

    def __init__(self, repo_root: Path, enable_rate_limiting: bool = True):
        """Initialize the Gemini CLI adapter.

        Args:
            repo_root: Repository root directory
            enable_rate_limiting: Whether to enable rate limiting
        """
        self.repo_root = repo_root
        self.enable_rate_limiting = enable_rate_limiting
        if enable_rate_limiting:
            self.rate_limiter = get_rate_limiter()
        else:
            self.rate_limiter = None

    def execute_prompt(
        self,
        policy: PromptPolicy,
        prompt_text: str,
        output_path: Path,
        context_data: Optional[str] = None,
        dry_run: bool = False,
    ) -> tuple[int, str, datetime, datetime, int]:
        """Execute a prompt via Gemini CLI.

        Args:
            policy: Prompt policy configuration
            prompt_text: The prompt to execute
            output_path: Path to write output
            context_data: Optional context data to append to prompt
            dry_run: If True, skip actual execution

        Returns:
            Tuple of (exit_code, output, started_at, ended_at, retries)

        Raises:
            GeminiCLIError: If execution fails after all retries
        """
        started_at = datetime.now()
        retries = 0
        last_error = None

        # Build full prompt with context
        full_prompt = prompt_text
        if context_data:
            full_prompt = f"{prompt_text}\n\n{context_data}"

        # Dry run mode
        if dry_run:
            return (
                0,
                "[DRY RUN] Would execute Gemini CLI",
                started_at,
                datetime.now(),
                0,
            )

        # Retry loop
        for attempt in range(policy.max_retries + 1):
            try:
                # Wait for rate limiter token if enabled
                if self.rate_limiter:
                    try:
                        self.rate_limiter.wait_if_needed(timeout=120.0)
                    except RateLimitError as e:
                        # Daily limit exceeded - fail immediately
                        ended_at = datetime.now()
                        raise GeminiCLIError(f"Rate limit exceeded: {e}") from e

                exit_code, output = self._invoke_gemini_cli(
                    prompt=full_prompt,
                    model=policy.model,
                    temperature=policy.temperature,
                    timeout_sec=policy.timeout_sec,
                    output_path=output_path,
                )

                ended_at = datetime.now()

                if exit_code == 0:
                    retries = attempt  # Track number of attempts before success
                    return (exit_code, output, started_at, ended_at, retries)
                else:
                    # Check if this is a rate limit error
                    is_rate_limit = self._is_rate_limit_error(output)

                    # Capture stderr in error message
                    last_error = f"Gemini CLI exited with code {exit_code}: {output[:500]}"
                    retries = attempt

                    # Retry with exponential backoff
                    if attempt < policy.max_retries:
                        if is_rate_limit:
                            # Longer backoff for rate limits (30-120 seconds)
                            backoff_time = min(30 * (2 ** attempt), 120)
                        else:
                            # Standard exponential backoff
                            backoff_time = min(2 ** attempt, 60)
                        time.sleep(backoff_time)

            except subprocess.TimeoutExpired as e:
                last_error = f"Timeout after {policy.timeout_sec}s"
                retries = attempt

                if attempt < policy.max_retries:
                    backoff_time = min(2 ** attempt, 60)
                    time.sleep(backoff_time)

            except Exception as e:
                last_error = str(e)
                retries = attempt

                if attempt < policy.max_retries:
                    backoff_time = min(2 ** attempt, 60)
                    time.sleep(backoff_time)

        ended_at = datetime.now()
        raise GeminiCLIError(
            f"Failed to execute prompt '{policy.prompt_id}' after "
            f"{policy.max_retries + 1} attempts. Last error: {last_error}"
        )

    def _invoke_gemini_cli(
        self,
        prompt: str,
        model: str,
        temperature: float,
        timeout_sec: int,
        output_path: Path,
    ) -> tuple[int, str]:
        """Invoke the Gemini CLI.

        Args:
            prompt: Prompt text
            model: Model name
            temperature: Temperature setting
            timeout_sec: Timeout in seconds
            output_path: Path to write output

        Returns:
            Tuple of (exit_code, stdout)
        """
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build command (Gemini CLI doesn't support --temperature flag)
        cmd = [
            "gemini",
            "--model",
            model,
            prompt,
        ]

        # Prepare environment - inherit current env and ensure Gemini settings
        import os
        env = os.environ.copy()

        # Ensure GEMINI_APPROVAL_MODE is set (default to yolo for automation)
        if "GEMINI_APPROVAL_MODE" not in env:
            env["GEMINI_APPROVAL_MODE"] = "yolo"

        try:
            # Execute with timeout
            result = subprocess.run(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout_sec,
                text=True,
                cwd=str(self.repo_root),
                env=env,
            )

            # Write output to file
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(result.stdout)

            # If command failed, include stderr in return
            if result.returncode != 0:
                error_msg = result.stderr if result.stderr else f"Exit code {result.returncode}"
                return result.returncode, error_msg

            return result.returncode, result.stdout

        except subprocess.TimeoutExpired as e:
            # Kill the process
            if e.args and len(e.args) > 0:
                try:
                    # Try to terminate gracefully
                    e.args[0].terminate()
                    time.sleep(2)
                    # Force kill if still running
                    e.args[0].kill()
                except:
                    pass

            raise

    def check_gemini_cli_available(self) -> bool:
        """Check if Gemini CLI is available.

        Returns:
            True if Gemini CLI is available
        """
        try:
            result = subprocess.run(
                ["gemini", "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
            )
            return result.returncode == 0
        except:
            return False

    def get_gemini_version(self) -> Optional[str]:
        """Get Gemini CLI version.

        Returns:
            Version string or None if not available
        """
        try:
            result = subprocess.run(
                ["gemini", "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
                text=True,
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except:
            return None

    def _is_rate_limit_error(self, error_output: str) -> bool:
        """Detect if error is due to rate limiting.

        Args:
            error_output: stderr or error message from Gemini CLI

        Returns:
            True if this appears to be a rate limit error
        """
        if not error_output:
            return False

        error_lower = error_output.lower()
        rate_limit_indicators = [
            "429",  # HTTP 429 Too Many Requests
            "rate limit",
            "quota exceeded",
            "too many requests",
            "resource exhausted",
            "requests per minute",
        ]

        return any(indicator in error_lower for indicator in rate_limit_indicators)
