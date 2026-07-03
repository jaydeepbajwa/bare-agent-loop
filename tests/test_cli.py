import os
import tempfile
import unittest
from pathlib import Path

from bare_agent.__main__ import load_dotenv, resolve_env_file


class CliTests(unittest.TestCase):
    def test_resolve_env_file_falls_back_to_repo_root(self) -> None:
        with tempfile.TemporaryDirectory() as current_directory:
            with tempfile.TemporaryDirectory() as repo_directory:
                repo_root = Path(repo_directory)
                repo_env = repo_root / ".env"
                repo_env.write_text("OPENAI_MODEL=repo-model\n", encoding="utf-8")

                previous_directory = os.getcwd()
                try:
                    os.chdir(current_directory)
                    resolved = resolve_env_file(Path(".env"), repo_root)
                finally:
                    os.chdir(previous_directory)

                self.assertEqual(resolved, repo_env.resolve())

    def test_load_dotenv_does_not_overwrite_existing_environment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text("OPENAI_MODEL=file-model\n", encoding="utf-8")

            previous_value = os.environ.get("OPENAI_MODEL")
            os.environ["OPENAI_MODEL"] = "shell-model"
            try:
                loaded = load_dotenv(env_file)
                self.assertTrue(loaded)
                self.assertEqual(os.environ["OPENAI_MODEL"], "shell-model")
            finally:
                if previous_value is None:
                    os.environ.pop("OPENAI_MODEL", None)
                else:
                    os.environ["OPENAI_MODEL"] = previous_value


if __name__ == "__main__":
    unittest.main()

