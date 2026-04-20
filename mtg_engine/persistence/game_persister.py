"""
Per-game MongoDB persister. Feature 026: normalized collections.
Writes to decisions, transcript, rules_qa, and games collections asynchronously.
All writes are fire-and-forget; failures are logged, never raised.
"""
import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MongoGamePersister:
    """
    Registers as a listener on GameExportStore recorders and persists
    game data to normalized MongoDB collections incrementally as events occur.
    """

    def __init__(self, game_id: str, games_col, decisions_col, rules_qa_col, transcript_col) -> None:
        self.game_id = game_id
        self._games_col = games_col
        self._decisions_col = decisions_col
        self._rules_qa_col = rules_qa_col
        self._transcript_col = transcript_col
        self._finalized = False
        self._sequence_counter = 0

    def _schedule(self, coro) -> None:
        """Schedule a coroutine safely from sync or async context."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(coro)
        except RuntimeError:
            from mtg_engine.persistence.mongo_client import get_main_loop
            loop = get_main_loop()
            if loop is not None and loop.is_running():
                asyncio.run_coroutine_threadsafe(coro, loop)
            else:
                logger.warning("MongoDB: no event loop available to schedule write for %s", self.game_id)

    # ── Registration ──────────────────────────────────────────────────────────

    def register_on_store(self, store) -> None:
        """Register self as listener on all four recorders."""
        store.transcript.register_listener(self._on_transcript_entry)
        store.snapshots.register_listener(self._on_snapshot_finalized)
        store.debug_log.register_listener(self._on_debug_entry)
        store.rules_qa.register_listener(self._on_rules_qa_entry)

    # ── Initial document insert ───────────────────────────────────────────────

    def init_game_document(
        self,
        player_1_name: str,
        player_1_type: str,
        player_2_name: str,
        player_2_type: str,
        format: str,
    ) -> None:
        self._schedule(self._do_init_game_document(
            player_1_name, player_1_type, player_2_name, player_2_type, format,
        ))

    async def _do_init_game_document(
        self,
        player_1_name: str,
        player_1_type: str,
        player_2_name: str,
        player_2_type: str,
        format: str,
    ) -> None:
        try:
            doc = {
                "_id": self.game_id,
                "game_id": self.game_id,
                "format": format,
                "player_1": {"name": player_1_name, "type": player_1_type},
                "player_2": {"name": player_2_name, "type": player_2_type},
                "has_human_player": (player_1_type == "human" or player_2_type == "human"),
                "created_at": _utcnow(),
                "completed_at": None,
                "is_complete": False,
                "outcome": None,
            }
            await self._games_col.update_one(
                {"_id": self.game_id},
                {"$setOnInsert": doc},
                upsert=True,
            )
        except Exception:
            logger.warning("MongoDB: failed to init game document for %s", self.game_id, exc_info=True)

    # ── Snapshot listener ─────────────────────────────────────────────────────

    def _on_snapshot_finalized(self, snap) -> None:
        self._sequence_counter += 1
        seq = self._sequence_counter
        self._schedule(self._upsert_decision(snap, seq))

    async def _upsert_decision(self, snap, sequence_number: int) -> None:
        try:
            active_player = snap.game_state.get("priority_holder") if isinstance(snap.game_state, dict) else None
            doc_id = snap.snapshot_id
            await self._decisions_col.update_one(
                {"_id": doc_id},
                {
                    "$setOnInsert": {
                        "_id": doc_id,
                        "game_id": self.game_id,
                        "snapshot_id": doc_id,
                        "sequence_number": sequence_number,
                        "turn": snap.turn,
                        "phase": snap.phase,
                        "step": snap.step,
                        "active_player": active_player,
                        "board_state": snap.game_state,
                        "legal_actions": snap.legal_actions,
                        "created_at": _utcnow(),
                        "llm_reasoning": None,
                        "observer_evaluation": None,
                        "outcome_context": None,
                    },
                    "$set": {
                        "action_taken": snap.action_taken,
                        "action_taken_by": snap.action_taken_by,
                    },
                },
                upsert=True,
            )
        except Exception:
            logger.warning("MongoDB: failed to upsert decision for snapshot %s", snap.snapshot_id, exc_info=True)

    # ── Debug entry listener ──────────────────────────────────────────────────

    def _on_debug_entry(self, entry) -> None:
        if entry.is_complete and entry.snapshot_id is not None:
            self._schedule(self._upsert_decision_from_debug(entry))

    async def _upsert_decision_from_debug(self, entry) -> None:
        try:
            if entry.entry_type.value == "prompt_response":
                sub_doc = {
                    "entry_id": entry.entry_id,
                    "prompt": entry.prompt,
                    "thinking": entry.thinking,
                    "response": entry.response,
                    "rating": entry.rating,
                    "player_annotation": entry.player_annotation,
                    "player_rating_override": entry.player_rating_override,
                }
                await self._decisions_col.update_one(
                    {"_id": entry.snapshot_id},
                    {"$set": {"llm_reasoning": sub_doc}},
                )
            elif entry.entry_type.value == "commentary":
                sub_doc = {
                    "entry_id": entry.entry_id,
                    "related_entry_id": entry.related_entry_id,
                    "prompt": entry.prompt,
                    "thinking": entry.thinking,
                    "response": entry.response,
                    "rating": entry.rating,
                    "explanation": entry.explanation,
                    "alternative": entry.alternative,
                }
                await self._decisions_col.update_one(
                    {"_id": entry.snapshot_id},
                    {"$set": {"observer_evaluation": sub_doc}},
                )
        except Exception:
            logger.warning("MongoDB: failed to upsert debug entry %s into decisions", entry.entry_id, exc_info=True)

    # ── Transcript listener ───────────────────────────────────────────────────

    def _on_transcript_entry(self, entry) -> None:
        self._schedule(self._insert_transcript(entry))
        if getattr(entry, "event_type", None) == "game_end":
            self._schedule(self._finalize_game())

    async def _insert_transcript(self, entry) -> None:
        try:
            doc = entry.model_dump()
            doc["game_id"] = self.game_id
            doc["sequence_number"] = entry.seq
            await self._transcript_col.insert_one(doc)
        except Exception:
            logger.warning("MongoDB: failed to insert transcript entry for %s", self.game_id, exc_info=True)

    # ── Rules Q&A listener ────────────────────────────────────────────────────

    def _on_rules_qa_entry(self, entry) -> None:
        self._schedule(self._insert_rules_qa(entry))

    async def _insert_rules_qa(self, entry) -> None:
        try:
            doc = entry.model_dump()
            doc["_id"] = entry.qa_id
            await self._rules_qa_col.insert_one(doc)
        except Exception:
            logger.warning("MongoDB: failed to insert rules_qa entry for %s", self.game_id, exc_info=True)

    # ── Game finalization ─────────────────────────────────────────────────────

    async def _finalize_game(self) -> None:
        if self._finalized:
            return
        self._finalized = True
        try:
            from mtg_engine.api.game_manager import get_manager
            from mtg_engine.export.store import get_export_store
            from mtg_engine.export.outcome import build_outcome

            mgr = get_manager()
            try:
                gs = mgr.get(self.game_id)
            except KeyError:
                gs = None

            outcome_dict = None
            winner = None
            winning_player = None
            total_turns = None

            if gs is not None:
                store = get_export_store(self.game_id)
                outcome = build_outcome(
                    gs,
                    snapshot_count=len(store.snapshots.get_all()),
                    transcript_length=len(store.transcript.get_all()),
                )
                outcome_dict = outcome.model_dump()
                winner = outcome_dict.get("winner")
                winning_player = outcome_dict.get("winning_player")
                total_turns = outcome_dict.get("total_turns")

            await self._games_col.update_one(
                {"_id": self.game_id},
                {"$set": {
                    "is_complete": True,
                    "completed_at": _utcnow(),
                    "outcome": outcome_dict,
                }},
                upsert=True,
            )

            # Bulk-update all decisions with outcome_context via aggregation pipeline
            await self._decisions_col.update_many(
                {"game_id": self.game_id},
                [{"$set": {"outcome_context": {
                    "winner": winner,
                    "winning_player": winning_player,
                    "total_turns": total_turns,
                    "active_player_won": {"$eq": ["$active_player", winner]},
                }}}],
            )
        except Exception:
            logger.warning("MongoDB: failed to finalize game %s", self.game_id, exc_info=True)

    # ── Post-game annotation / rerate update ──────────────────────────────────

    def update_debug_entry(self, entry) -> None:
        """Schedule an in-place update for player_annotation and player_rating_override."""
        self._schedule(self._do_update_debug_entry(entry))

    async def _do_update_debug_entry(self, entry) -> None:
        try:
            snapshot_id = getattr(entry, "snapshot_id", None)
            if snapshot_id is None:
                return
            await self._decisions_col.update_one(
                {"_id": snapshot_id},
                {"$set": {
                    "llm_reasoning.player_annotation": entry.player_annotation,
                    "llm_reasoning.player_rating_override": entry.player_rating_override,
                }},
            )
        except Exception:
            logger.warning(
                "MongoDB: failed to update debug entry %s for game %s",
                entry.entry_id, self.game_id, exc_info=True,
            )
