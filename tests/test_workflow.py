import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from streamlit.testing.v1 import AppTest

import MAS_LangChain as workflow

APP_PATH = str(Path(__file__).resolve().parents[1] / "app.py")


SOURCES = [{"id": "S1", "title": "Industry report", "url": "https://example.org/report", "snippet": "Training demand is growing."}]
BRIEF = workflow.ActionBrief(executive_summary="Demand merits validation [S1].", key_findings=["Training demand [S1]."],
                             risks=["Snippet evidence is limited."], recommendations=["Literacy: interview HR buyers.",
                             "Role-based training: pilot with teams.", "Leadership workshops: test willingness to pay."])


class WorkflowTests(unittest.TestCase):
    def test_gemini_credentials_do_not_satisfy_openrouter_requirement(self):
        values = {"GEMINI_API_KEY": "old-test-key", "SERP_API_KEY": "search-test-key"}
        with patch.object(workflow, "setting", side_effect=lambda name: values.get(name, "")):
            self.assertEqual(workflow.missing_keys(), ["OPENROUTER_API_KEY"])

    def test_empty_input_does_not_call_search(self):
        with patch.object(workflow, "search_web") as search:
            for value in ("", "  ", None):
                with self.assertRaises(workflow.WorkflowError):
                    workflow.run_workflow(value)
            search.assert_not_called()

    def test_missing_keys(self):
        with patch.object(workflow, "setting", return_value=""):
            with self.assertRaisesRegex(workflow.WorkflowError, "OPENROUTER_API_KEY, SERP_API_KEY"):
                workflow.run_workflow("Demand for training?")

    def test_sequential_workflow_and_source_propagation(self):
        for question in (workflow.EXAMPLE_QUESTION, "How can a local bakery reduce food waste?"):
            with self.subTest(question=question):
                calls = []

                def respond(prompt):
                    text = prompt.to_string()
                    calls.append(text)
                    self.assertIn(question, text)
                    self.assertIn(SOURCES[0]["url"], text)
                    return AIMessage(content="Research facts [S1]" if len(calls) == 1 else "Analysis findings [S1]")

                def finish(prompt):
                    text = prompt.to_string()
                    calls.append(text)
                    self.assertIn("Research facts [S1]", text)
                    self.assertIn("Analysis findings [S1]", text)
                    return BRIEF

                model = RunnableLambda(respond)
                model.with_structured_output = lambda schema, **kwargs: RunnableLambda(finish)
                with patch.object(workflow, "missing_keys", return_value=[]), \
                     patch.object(workflow, "setting", return_value="test-key"), \
                     patch.object(workflow, "search_web", return_value=SOURCES), \
                     patch.object(workflow, "ChatOpenRouter", return_value=model) as constructor:
                    result = workflow.run_workflow(question)
                self.assertEqual(constructor.call_args.kwargs["api_key"], "test-key")
                self.assertNotIn("vertexai", constructor.call_args.kwargs)
                self.assertEqual(len(calls), 3)
                for heading in ("Executive Summary", "Key Findings", "Risks", "Recommendations and Next Steps", "Sources"):
                    self.assertIn("## " + heading, result)
                self.assertIn(SOURCES[0]["url"], result)
                self.assertIn("Literacy:", result)

    def test_no_results(self):
        response = Mock(status_code=200)
        response.json.return_value = {"organic_results": []}
        with patch.object(workflow.requests, "get", return_value=response):
            with self.assertRaisesRegex(workflow.WorkflowError, "No usable web results"):
                workflow.search_web("question", "secret")

    def test_search_filters_duplicates_and_unsafe_links(self):
        response = Mock(status_code=200)
        response.json.return_value = {"organic_results": [
            {"title": "Valid", "link": "https://example.org", "snippet": "Evidence"},
            {"link": "https://example.org"}, {"link": "javascript:alert(1)"}, None]}
        with patch.object(workflow.requests, "get", return_value=response):
            sources = workflow.search_web("question", "secret")
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["id"], "S1")

    def test_search_errors_do_not_expose_secrets(self):
        with patch.object(workflow.requests, "get", side_effect=requests.Timeout("api_key=SECRET")):
            with self.assertRaises(workflow.WorkflowError) as error:
                workflow.search_web("question", "SECRET")
        self.assertNotIn("SECRET", str(error.exception))
        for status in (401, 403, 429):
            response = Mock(status_code=status)
            with patch.object(workflow.requests, "get", return_value=response):
                with self.assertRaises(workflow.WorkflowError):
                    workflow.search_web("question", "SECRET")

    def test_model_errors_do_not_expose_secrets(self):
        with patch.object(workflow, "missing_keys", return_value=[]), \
             patch.object(workflow, "setting", return_value="SECRET"), \
             patch.object(workflow, "search_web", return_value=SOURCES), \
             patch.object(workflow, "ChatOpenRouter", side_effect=RuntimeError("SECRET")):
            with self.assertRaises(workflow.WorkflowError) as error:
                workflow.run_workflow("A business question")
        self.assertNotIn("SECRET", str(error.exception))
        self.assertIn("Researcher", str(error.exception))


class DashboardTests(unittest.TestCase):
    def test_missing_key_setup(self):
        with patch.object(workflow, "missing_keys", return_value=["OPENROUTER_API_KEY"]):
            app = AppTest.from_file(APP_PATH).run()
        self.assertFalse(app.exception)
        self.assertTrue(app.button[0].disabled)
        self.assertEqual(app.text_area[0].value, workflow.EXAMPLE_QUESTION)

    def test_generate_persist_and_clear_after_failure(self):
        with patch.object(workflow, "missing_keys", return_value=[]), \
             patch.object(workflow, "run_workflow", return_value=workflow.render_brief(BRIEF, SOURCES)) as run:
            app = AppTest.from_file(APP_PATH).run()
            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertIn("## Executive Summary", app.session_state["brief"])
            self.assertEqual(len(app.get("download_button")), 1)
            app.run()
            self.assertEqual(run.call_count, 1)
            run.side_effect = workflow.WorkflowError("Quota exhausted")
            app.text_area[0].set_value("Another question")
            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.get("download_button")), 0)
            self.assertIn("Quota exhausted", app.error[0].value)

    def test_empty_submission(self):
        with patch.object(workflow, "missing_keys", return_value=[]), patch.object(workflow, "run_workflow") as run:
            app = AppTest.from_file(APP_PATH).run()
            app.text_area[0].set_value("   ")
            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertTrue(app.warning)
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
