"""WorkFragmentRef — record that a fragment was *included* into a work (M8).

This row is created by the include-fragment-into-work flow. It powers the
"this fragment is used by these works" reverse lookup. It does NOT enforce
content sync — the included text is captured at the moment of inclusion
and may be edited freely on either side afterwards.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class WorkFragmentRef:
    id: str
    work_id: str
    section_id: Optional[str]
    entry_id: str
    included_text: str = ""
    created_at: Optional[str] = None
