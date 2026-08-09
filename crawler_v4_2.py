#!/usr/bin/env python3
"""Academic Job Bot v4.2 entry point.

Runs the preserved v4.1 crawler with the v4.2 discovery/extraction reliability
patches applied at runtime. The original crawler.py remains unchanged so the
new behavior can be verified before promotion.
"""

import crawler
from utils.crawler_v42_patch import apply

apply(crawler)

if __name__ == "__main__":
    import sys
    if "--self-test" in sys.argv:
        raise SystemExit(crawler.self_test())
    crawler.main()
