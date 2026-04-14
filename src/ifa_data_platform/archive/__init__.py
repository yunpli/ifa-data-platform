"""iFA Archive Layer Framework.

A separate line for long-term asset accumulation and backfill.
NOT for same-day report production.

Archive is designed to run in night windows that do not compete with
lowfreq/midfreq production windows.

Default windows (Asia/Shanghai):
- window_1: 21:30-22:30
- window_2: 02:00-03:00

Business time standard: Asia/Shanghai
"""

__version__ = "0.1.0"
