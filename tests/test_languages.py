import pytest
from pydantic import ValidationError

from app.languages import (
    LanguageAlreadyExistsError,
    LanguageNotFoundError,
    LanguageRegistry,
)
from app.models import LanguageConfig


def test_registry_has_default_python_language():
    registry = LanguageRegistry()

    assert registry.list_languages() == ["python"]

    python_config = registry.get_language("python")
    assert python_config.name == "python"
    assert python_config.file_ext == ".py"
    assert python_config.run_cmd == "python {src}"


def test_registry_registers_new_language():
    registry = LanguageRegistry()

    registry.register_language(
        LanguageConfig(
            name="cpp",
            file_ext=".cpp",
            compile_cmd="g++ {src} -o {exe}",
            run_cmd="{exe}",
            time_limit=3.0,
            memory_limit=128,
        )
    )

    assert registry.list_languages() == ["cpp", "python"]
    assert registry.get_language("cpp").file_ext == ".cpp"


def test_registry_rejects_duplicate_language():
    registry = LanguageRegistry()

    with pytest.raises(LanguageAlreadyExistsError):
        registry.register_language(
            LanguageConfig(
                name="python",
                file_ext=".py",
                run_cmd="python {src}",
            )
        )


def test_registry_rejects_missing_language():
    registry = LanguageRegistry()

    with pytest.raises(LanguageNotFoundError):
        registry.get_language("cpp")


def test_language_config_rejects_invalid_data():
    with pytest.raises(ValidationError):
        LanguageConfig(
            name="",
            file_ext=".py",
            run_cmd="python {src}",
        )

    with pytest.raises(ValidationError):
        LanguageConfig(
            name="go",
            file_ext=".go",
            run_cmd="",
        )

    with pytest.raises(ValidationError):
        LanguageConfig(
            name="rust",
            file_ext=".rs",
            run_cmd="rustc {src}",
            time_limit=0,
        )