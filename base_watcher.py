"""
Base Watcher
Foundation class for all watcher scripts in the AI Employee system.
All watchers (Gmail, WhatsApp, LinkedIn, FileSystem) inherit from this.
"""

import time
import logging
from pathlib import Path
from abc import ABC, abstractmethod
from datetime import datetime


class BaseWatcher(ABC):
    def __init__(self, vault_path: str, check_interval: int = 60):
        self.vault_path = Path(vault_path)
        self.needs_action = self.vault_path / "Needs_Action"
        self.check_interval = check_interval
        self.logger = self._setup_logger()
        self.processed_ids: set = set()
        self._ensure_directories()

    def _setup_logger(self) -> logging.Logger:
        """Setup logger for this watcher."""
        logs_dir = self.vault_path / "Logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        logger = logging.getLogger(self.__class__.__name__)
        logger.setLevel(logging.INFO)

        if logger.handlers:
            return logger

        # File handler
        log_file = logs_dir / f"{self.__class__.__name__.lower()}.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Formatter
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    def _ensure_directories(self):
        """Create required vault directories if missing."""
        dirs = [
            self.needs_action,
            self.vault_path / "Logs",
            self.vault_path / "Done",
            self.vault_path / "Pending_Approval",
            self.vault_path / "Approved",
            self.vault_path / "In_Progress",
            self.vault_path / "Failed",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    def _generate_task_filename(self, source: str, subject: str) -> str:
        """
        Generate a unique task filename.
        Format: task_YYYYMMDDHHMMSS_source_subject.md
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        # Clean subject for filename
        clean_subject = "".join(
            c if c.isalnum() or c in "-_" else "_"
            for c in subject[:50]
        ).strip("_")
        return f"task_{timestamp}_{source}_{clean_subject}.md"

    def _write_action_file(self, filename: str, content: str) -> Path:
        """
        Write a task file to Needs_Action folder.
        Returns the path of the created file.
        """
        filepath = self.needs_action / filename
        filepath.write_text(content, encoding="utf-8")
        self.logger.info(f"📝 Created task: {filename}")
        return filepath

    def _is_already_processed(self, item_id: str) -> bool:
        """Check if an item has already been processed this session."""
        return item_id in self.processed_ids

    def _mark_as_processed(self, item_id: str):
        """Mark an item as processed to avoid duplicates."""
        self.processed_ids.add(item_id)

    @abstractmethod
    def check_for_updates(self) -> list:
        """
        Check source for new items to process.
        Must return a list of new items.
        """
        pass

    @abstractmethod
    def create_action_file(self, item) -> Path:
        """
        Create a .md task file in Needs_Action folder.
        Must return the path of the created file.
        """
        pass

    def on_startup(self):
        """
        Called once when the watcher starts.
        Override to add custom startup logic.
        """
        pass

    def on_error(self, error: Exception):
        """
        Called when an error occurs during check_for_updates.
        Override to add custom error handling.
        """
        self.logger.error(f"Error in {self.__class__.__name__}: {error}")

    def run(self):
        """
        Main watcher loop.
        Continuously checks for updates at check_interval seconds.
        """
        self.logger.info(f"🚀 Starting {self.__class__.__name__}")
        self.logger.info(f"📁 Vault: {self.vault_path}")
        self.logger.info(f"⏱️  Interval: {self.check_interval}s")

        print(f"\n{'='*50}")
        print(f"👁️  {self.__class__.__name__} Running")
        print(f"📁 Watching: {self.needs_action}")
        print(f"⏱️  Check every: {self.check_interval}s")
        print(f"{'='*50}\n")

        # Run startup hook
        try:
            self.on_startup()
        except Exception as e:
            self.logger.warning(f"Startup hook failed: {e}")

        while True:
            try:
                items = self.check_for_updates()

                if items:
                    self.logger.info(f"Found {len(items)} new item(s)")
                    for item in items:
                        try:
                            filepath = self.create_action_file(item)
                            self.logger.info(f"✅ Task created: {filepath.name}")
                        except Exception as e:
                            self.logger.error(f"Failed to create task file: {e}")
                else:
                    self.logger.debug("No new items found")

            except KeyboardInterrupt:
                self.logger.info(f"{self.__class__.__name__} stopped by user")
                print(f"\n👋 {self.__class__.__name__} stopped")
                break
            except Exception as e:
                self.on_error(e)

            time.sleep(self.check_interval)

    def run_once(self) -> list:
        """
        Run a single check cycle without looping.
        Useful for testing and scheduled runs.
        Returns list of created file paths.
        """
        created_files = []
        try:
            items = self.check_for_updates()
            for item in items:
                filepath = self.create_action_file(item)
                created_files.append(filepath)
        except Exception as e:
            self.on_error(e)
        return created_files