from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional
import logging
from app.config import (
    RATE_LIMIT_ENABLED,
    USER_RATE_LIMIT_WINDOW,
    USER_RATE_LIMIT_MAX,
    TEAM_RATE_LIMIT_WINDOW,
    TEAM_RATE_LIMIT_MAX,
)


class UserRateLimiter:
    """
    Rate limiter for controlling how frequently users can interact with the Slack bot.
    Implements both per-user and per-team rate limits.
    """

    def __init__(
        self,
        user_window_seconds: int = USER_RATE_LIMIT_WINDOW,
        user_max_requests: int = USER_RATE_LIMIT_MAX,
        team_window_seconds: int = TEAM_RATE_LIMIT_WINDOW,
        team_max_requests: int = TEAM_RATE_LIMIT_MAX,
        enabled: bool = RATE_LIMIT_ENABLED,
    ):
        """
        Initialize the rate limiter with configurable windows and limits

        Args:
            user_window_seconds: Time window for user rate limiting in seconds
            user_max_requests: Maximum number of requests per user in the window
            team_window_seconds: Time window for team rate limiting in seconds
            team_max_requests: Maximum number of requests per team in the window
            enabled: Whether rate limiting is enabled
        """
        # Store user_id -> (request_count, timestamp of first request in window)
        self.user_requests: Dict[str, Tuple[int, datetime]] = {}

        # Store team_id -> (request_count, timestamp of first request in window)
        self.team_requests: Dict[str, Tuple[int, datetime]] = {}

        # Rate limit settings
        self.user_window_seconds = user_window_seconds
        self.user_max_requests = user_max_requests
        self.team_window_seconds = team_window_seconds
        self.team_max_requests = team_max_requests
        self.enabled = enabled

        # Stats for monitoring
        self.user_limit_hits = 0
        self.team_limit_hits = 0

        # For logging
        self.logger = logging.getLogger("rate_limiter")

    def is_rate_limited(
        self, user_id: str, team_id: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Check if a request from a user should be rate limited

        Args:
            user_id: The Slack user ID
            team_id: The Slack team/workspace ID (optional)

        Returns:
            Tuple of (is_limited, reason) where:
              - is_limited: True if the request should be rate-limited
              - reason: A string explaining why the request was rate-limited, or empty if not limited
        """
        # If rate limiting is disabled, always allow
        if not self.enabled:
            return False, ""

        current_time = datetime.now()
        reason = ""

        # Check user-level rate limit
        if user_id in self.user_requests:
            count, window_start = self.user_requests[user_id]

            # If window has expired, reset
            if current_time - window_start > timedelta(
                seconds=self.user_window_seconds
            ):
                self.user_requests[user_id] = (1, current_time)
            else:
                # If within window and over limit
                if count >= self.user_max_requests:
                    self.user_limit_hits += 1
                    reason = f"User rate limit exceeded: {count} requests in {self.user_window_seconds} seconds"
                    # Don't increment the counter for this request as it's being blocked
                    return True, reason

                # Increment count
                self.user_requests[user_id] = (count + 1, window_start)
        else:
            # First request from user
            self.user_requests[user_id] = (1, current_time)

        # If team_id is provided, check team-level rate limit
        if team_id:
            if team_id in self.team_requests:
                team_count, team_window_start = self.team_requests[team_id]

                if current_time - team_window_start > timedelta(
                    seconds=self.team_window_seconds
                ):
                    self.team_requests[team_id] = (1, current_time)
                else:
                    if team_count >= self.team_max_requests:
                        self.team_limit_hits += 1
                        reason = f"Team rate limit exceeded: {team_count} requests in {self.team_window_seconds} seconds"
                        return True, reason
                    self.team_requests[team_id] = (team_count + 1, team_window_start)
            else:
                self.team_requests[team_id] = (1, current_time)

        return False, reason

    def get_remaining_requests(
        self, user_id: str, team_id: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Get the number of remaining requests allowed for a user and their team

        Args:
            user_id: The Slack user ID
            team_id: The Slack team/workspace ID (optional)

        Returns:
            Dictionary with the remaining user and team requests
        """
        # If rate limiting is disabled, return maximum values
        if not self.enabled:
            return {
                "user_remaining": self.user_max_requests,
                "team_remaining": self.team_max_requests if team_id else None,
                "user_window_reset_seconds": 0,
                "team_window_reset_seconds": 0,
            }

        current_time = datetime.now()
        result = {
            "user_remaining": self.user_max_requests,
            "team_remaining": self.team_max_requests if team_id else None,
        }

        # Check user remaining
        if user_id in self.user_requests:
            count, window_start = self.user_requests[user_id]

            # If window is still active
            if current_time - window_start <= timedelta(
                seconds=self.user_window_seconds
            ):
                result["user_remaining"] = max(0, self.user_max_requests - count)
                # Add time remaining in window
                seconds_elapsed = (current_time - window_start).total_seconds()
                result["user_window_reset_seconds"] = max(
                    0, self.user_window_seconds - seconds_elapsed
                )

        # Check team remaining
        if team_id and team_id in self.team_requests:
            team_count, team_window_start = self.team_requests[team_id]

            # If window is still active
            if current_time - team_window_start <= timedelta(
                seconds=self.team_window_seconds
            ):
                result["team_remaining"] = max(0, self.team_max_requests - team_count)
                # Add time remaining in window
                seconds_elapsed = (current_time - team_window_start).total_seconds()
                result["team_window_reset_seconds"] = max(
                    0, self.team_window_seconds - seconds_elapsed
                )

        return result

    def get_stats(self) -> Dict[str, int]:
        """Get statistics about rate limiting activity"""
        return {
            "user_limit_hits": self.user_limit_hits,
            "team_limit_hits": self.team_limit_hits,
            "active_user_windows": len(self.user_requests),
            "active_team_windows": len(self.team_requests),
            "enabled": self.enabled,
        }

    def clear_expired_entries(self):
        """Clear expired rate limit entries to prevent memory growth"""
        if not self.enabled:
            return 0, 0

        current_time = datetime.now()

        # Clear expired user entries
        expired_users = []
        for user_id, (_, window_start) in self.user_requests.items():
            if current_time - window_start > timedelta(
                seconds=self.user_window_seconds
            ):
                expired_users.append(user_id)

        for user_id in expired_users:
            del self.user_requests[user_id]

        # Clear expired team entries
        expired_teams = []
        for team_id, (_, window_start) in self.team_requests.items():
            if current_time - window_start > timedelta(
                seconds=self.team_window_seconds
            ):
                expired_teams.append(team_id)

        for team_id in expired_teams:
            del self.team_requests[team_id]

        return len(expired_users), len(expired_teams)


# Create a singleton instance
user_rate_limiter = UserRateLimiter()
