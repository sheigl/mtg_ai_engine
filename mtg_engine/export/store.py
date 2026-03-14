"""
Per-game export store. Holds SnapshotRecorder, TranscriptRecorder,
RulesQARecorder for each active game.
"""
from mtg_engine.export.snapshots import SnapshotRecorder
from mtg_engine.export.transcript import TranscriptRecorder
from mtg_engine.export.rules_qa import RulesQARecorder


class GameExportStore:
    def __init__(self, game_id: str) -> None:
        self.game_id = game_id
        self.snapshots = SnapshotRecorder(game_id)
        self.transcript = TranscriptRecorder(game_id)
        self.rules_qa = RulesQARecorder(game_id)


_store: dict[str, GameExportStore] = {}


def get_export_store(game_id: str) -> GameExportStore:
    if game_id not in _store:
        _store[game_id] = GameExportStore(game_id)
    return _store[game_id]


def delete_export_store(game_id: str) -> GameExportStore | None:
    return _store.pop(game_id, None)
