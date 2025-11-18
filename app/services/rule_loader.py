"""
심사 규칙 로더
"""
from pathlib import Path
from typing import List
import structlog

from app.config import settings
from app.core.exceptions import RuleLoadException

logger = structlog.get_logger()


class RuleLoader:
    """심사 규칙 파일을 로드하는 서비스"""

    def __init__(self):
        self.rules_dir = settings.rules_dir

    def load_rules(self, rules_files: List[str]) -> str:
        """
        여러 규칙 파일을 로드하여 하나의 문자열로 반환

        Args:
            rules_files: 로드할 규칙 파일 목록

        Returns:
            결합된 규칙 내용

        Raises:
            RuleLoadException: 규칙 파일 로드 실패 시
        """
        combined_rules = []

        for rule_file in rules_files:
            rule_path = self.rules_dir / rule_file

            if not rule_path.exists():
                logger.error("rule_file_not_found", file=rule_file, path=str(rule_path))
                raise RuleLoadException(
                    f"Rule file not found: {rule_file}",
                    details={"file": rule_file, "path": str(rule_path)},
                )

            try:
                logger.info("loading_rule_file", file=rule_file)
                content = rule_path.read_text(encoding="utf-8")
                combined_rules.append(f"# {rule_file}\n\n{content}")
                logger.info("rule_file_loaded", file=rule_file, size=len(content))

            except Exception as e:
                logger.exception("failed_to_read_rule_file", file=rule_file, error=str(e))
                raise RuleLoadException(
                    f"Failed to read rule file: {rule_file}",
                    details={"file": rule_file, "error": str(e)},
                )

        combined = "\n\n---\n\n".join(combined_rules)
        logger.info(
            "rules_loaded",
            files_count=len(rules_files),
            total_size=len(combined),
        )

        return combined

    def get_available_rules(self) -> List[str]:
        """
        사용 가능한 규칙 파일 목록 반환

        Returns:
            규칙 파일 이름 목록
        """
        try:
            if not self.rules_dir.exists():
                logger.warning("rules_directory_not_found", path=str(self.rules_dir))
                return []

            rules = [f.name for f in self.rules_dir.glob("*.md")]
            logger.info("available_rules_listed", count=len(rules))
            return sorted(rules)

        except Exception as e:
            logger.exception("failed_to_list_rules", error=str(e))
            return []
