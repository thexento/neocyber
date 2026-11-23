"""Expandable activity entries backed by real ActivityEvent records."""
from __future__ import annotations

from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Static

from neocyber.models.activity import ActivityEvent


class ActivityCard(Widget):
    """A minimal, sleek activity entry. Left-click to inspect details."""

    DEFAULT_CSS = """
    ActivityCard {
        width: 100%;
        height: auto;
        margin: 0 0 0 2;
        padding: 0;
    }
    .activity-header {
        color: #71717a;
        height: 1;
    }
    .activity-detail {
        display: none;
        color: #a1a1aa;
        background: #111113;
        padding: 0 1;
        margin-top: 0;
        margin-bottom: 1;
        height: auto;
        max-height: 14;
        overflow-y: auto;
        border-left: thin #38bdf8;
    }
    ActivityCard.expanded .activity-detail {
        display: block;
    }
    """

    def __init__(self, event: ActivityEvent, id: str | None = None) -> None:
        super().__init__(id=id)
        self.event = event
        self.expanded = False

    def compose(self) -> ComposeResult:
        dur = f" · {self.event.duration:.1f}s" if self.event.duration is not None else ""
        icon = {"command": "⚡", "file_read": "📖", "file_edit": "✏️", "verification": "✓", "error": "!"}.get(self.event.type, "•")
        status = " (running...)" if self.event.status == "running" else ""
        
        style = "#38bdf8" if self.event.status == "running" else ("#f87171" if self.event.status == "failed" else "#71717a")
        yield Static(Text(f"› {icon} {self.event.summary}{dur}{status}", style=style), classes="activity-header")
        details = self._details() or "(No additional output)"
        yield Static(details, classes="activity-detail")

    def _details(self) -> str:
        pieces = []
        if self.event.arguments.get("command"):
            pieces.append(f"$ {self.event.arguments['command']}")
        if self.event.result:
            pieces.append(self.event.result)
        if self.event.status == "failed" and "status: failed" not in pieces:
            pieces.append("status: failed")
        return "\n".join(pieces)

    def on_click(self, event: events.Click) -> None:
        # ONLY expand on left-click (button 1) — NEVER right-click
        if getattr(event, "button", 1) != 1:
            return
        self.expanded = not self.expanded
        self.set_class(self.expanded, "expanded")

    def on_key(self, event: events.Key) -> None:
        if event.key in ("enter", "space"):
            self.expanded = not self.expanded
            self.set_class(self.expanded, "expanded")
            event.stop()


class ActivityGroup(Widget):
    """Clean per-task activity stage grouping child events."""

    DEFAULT_CSS = """
    ActivityGroup {
        width: 100%;
        height: auto;
        margin: 0 0 1 0;
        padding: 0 1;
    }
    .group-header {
        color: #52525b;
        height: 1;
    }
    .group-events {
        display: none;
        height: auto;
    }
    ActivityGroup.expanded .group-events {
        display: block;
    }
    """

    def __init__(self, task_id: str, id: str | None = None) -> None:
        super().__init__(id=id)
        self.task_id = task_id
        self.events: dict[str, ActivityEvent] = {}
        self.expanded = False

    def compose(self) -> ComposeResult:
        yield Static("› + 0 activities", classes="group-header", id=f"{self.id}-header")
        yield Vertical(classes="group-events", id=f"{self.id}-events")

    def upsert(self, event: ActivityEvent) -> None:
        # Filter out empty or raw thought clutter
        if event.type == "thought" and not event.summary.strip():
            return
        self.events[event.event_id] = event
        try:
            self.query_one(f"#{self.id}-header", Static).update("› " + self._summary())
            child_id = f"event-{event.event_id[:12]}"
            try:
                card = self.query_one(f"#{child_id}", ActivityCard)
                card.event = event
                card.refresh(recompose=True)
            except Exception:
                self.query_one(f"#{self.id}-events", Vertical).mount(ActivityCard(event, id=child_id))
        except Exception:
            pass

    def _summary(self) -> str:
        counts: dict[str, int] = {}
        for event in self.events.values():
            if event.type != "activity_summary":
                counts[event.type] = counts.get(event.type, 0) + 1
        labels = {"command": "commands", "file_read": "reads", "file_edit": "edits", "error": "errors"}
        body = ", ".join(f"{count} {labels.get(kind, kind)}" for kind, count in counts.items() if kind in labels)
        return "+ " + (body or "activities")

    def on_click(self, event: events.Click) -> None:
        # ONLY expand on left-click (button 1) — NEVER right-click
        if getattr(event, "button", 1) != 1:
            return
        self.expanded = not self.expanded
        self.set_class(self.expanded, "expanded")
