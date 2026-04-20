"""
Per-game export store. Holds SnapshotRecorder, TranscriptRecorder,
RulesQARecorder, DebugLogRecorder for each active game.
"""
from mtg_engine.export.snapshots import SnapshotRecorder
from mtg_engine.export.transcript import TranscriptRecorder
from mtg_engine.export.rules_qa import RulesQARecorder
from mtg_engine.export.debug_log import DebugLogRecorder


class GameExportStore:
    def __init__(self, game_id: str) -> None:
        self.game_id = game_id
        self.snapshots = SnapshotRecorder(game_id)
        self.transcript = TranscriptRecorder(game_id)
        self.rules_qa = RulesQARecorder(game_id)
        self.debug_log = DebugLogRecorder(game_id)
        self.persister = None  # set by get_export_store when MongoDB is configured
        self.current_snapshot_id: str | None = None


_store: dict[str, GameExportStore] = {}


def get_export_store(game_id: str) -> GameExportStore:
    if game_id not in _store:
        store = GameExportStore(game_id)
        from mtg_engine.persistence.mongo_client import (
            is_configured, get_games_collection,
            get_decisions_collection, get_rules_qa_collection, get_transcript_collection,
        )
        if is_configured():
            from mtg_engine.persistence.game_persister import MongoGamePersister
            store.persister = MongoGamePersister(
                game_id,
                get_games_collection(),
                get_decisions_collection(),
                get_rules_qa_collection(),
                get_transcript_collection(),
            )
        _store[game_id] = store
    return _store[game_id]


def delete_export_store(game_id: str) -> GameExportStore | None:
    return _store.pop(game_id, None)
