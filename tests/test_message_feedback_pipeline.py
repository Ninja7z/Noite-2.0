import asyncio
import shutil
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace

from fastapi import HTTPException

import integrations.openwebui.noite_api as api
from noite.assistant import AssistantService
from noite.store import add_message, open_database, recent_messages_extended, set_message_feedback


class MessageFeedbackPipelineTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="noite-feedback-test-"))
        self.service = AssistantService(settings=SimpleNamespace(data_dir=str(self.temp_dir)))
        self.original_service = api.service
        api.service = self.service
        with closing(open_database(self.service.database_path)) as connection, connection:
            connection.execute(
                "INSERT OR IGNORE INTO conversations(id, title) VALUES ('active', 'Ativa')"
            )
            connection.execute(
                "INSERT OR IGNORE INTO conversations(id, title) VALUES ('other', 'Outra')"
            )
            self.user_id = add_message(connection, "user", "Pergunta", conversation_id="active")
            self.assistant_id = add_message(
                connection, "assistant", "Resposta", conversation_id="active"
            )
            self.other_id = add_message(
                connection, "assistant", "Resposta externa", conversation_id="other"
            )

    def tearDown(self):
        api.service = self.original_service
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    async def expect_http(self, status: int, payload: api.FeedbackPayload):
        with self.assertRaises(HTTPException) as raised:
            await api.web_feedback(payload, {"active": "active"})
        self.assertEqual(raised.exception.status_code, status)

    async def test_feedback_upsert_remove_and_cascade(self):
        """1. SQLite: Testar UPSERT, remoção e cascata ON DELETE no banco de dados."""
        with closing(open_database(self.service.database_path)) as connection, connection:
            set_message_feedback(connection, self.assistant_id, "positive")
            self.assertEqual(
                recent_messages_extended(connection, "active")[-1]["rating"], "positive"
            )
            set_message_feedback(connection, self.assistant_id, "negative")
            self.assertEqual(
                recent_messages_extended(connection, "active")[-1]["rating"], "negative"
            )
            set_message_feedback(connection, self.assistant_id, None)
            self.assertIsNone(recent_messages_extended(connection, "active")[-1]["rating"])
            set_message_feedback(connection, self.assistant_id, "positive")
            connection.execute("DELETE FROM messages WHERE id = ?", (self.assistant_id,))
            self.assertIsNone(
                connection.execute(
                    "SELECT 1 FROM message_feedback WHERE message_id = ?", (self.assistant_id,)
                ).fetchone()
            )

    async def test_api_security_validations(self):
        """2. API: Validar rejeições estritas (404 inexistente, 403 conversa alheia,
        400 user role e 400 rating inválido)."""
        await self.expect_http(404, api.FeedbackPayload(message_id=999999, rating="positive"))
        await self.expect_http(
            403, api.FeedbackPayload(message_id=self.other_id, rating="positive")
        )
        await self.expect_http(400, api.FeedbackPayload(message_id=self.user_id, rating="positive"))
        await self.expect_http(
            400, api.FeedbackPayload(message_id=self.assistant_id, rating="invalid")
        )

    async def test_api_vote_positive_and_negative_success(self):
        """3. API: Validar submissão bem-sucedida de votos positivos e negativos."""
        saved_pos = await api.web_feedback(
            api.FeedbackPayload(message_id=self.assistant_id, rating="positive"),
            {"active": "active"},
        )
        self.assertTrue(saved_pos["ok"])
        self.assertEqual(saved_pos["rating"], "positive")
        self.assertEqual(self.service.history_extended("active")[-1]["rating"], "positive")

        saved_neg = await api.web_feedback(
            api.FeedbackPayload(message_id=self.assistant_id, rating="negative"),
            {"active": "active"},
        )
        self.assertTrue(saved_neg["ok"])
        self.assertEqual(saved_neg["rating"], "negative")
        self.assertEqual(self.service.history_extended("active")[-1]["rating"], "negative")

    async def test_api_vote_removal(self):
        """4. API: Validar remoção de voto quando rating é None ou vazio."""
        await api.web_feedback(
            api.FeedbackPayload(message_id=self.assistant_id, rating="positive"),
            {"active": "active"},
        )
        self.assertEqual(self.service.history_extended("active")[-1]["rating"], "positive")
        removed = await api.web_feedback(
            api.FeedbackPayload(message_id=self.assistant_id, rating=None), {"active": "active"}
        )
        self.assertTrue(removed["ok"])
        self.assertIsNone(removed["rating"])
        self.assertIsNone(self.service.history_extended("active")[-1]["rating"])

    async def test_saved_turn_ids_are_scoped_to_request_task(self):
        """5. AssistantService: Validar escopo de IDs de turno por Task concorrente."""

        async def save():
            return self.service._save_turn("active", "Outra pergunta", "Outra resposta")

        task = asyncio.create_task(save())
        ids = await task
        self.assertEqual(self.service.get_last_saved_turn("active", task), ids)
        self.assertIsNone(self.service.get_last_saved_turn("active", task))


if __name__ == "__main__":
    unittest.main()
