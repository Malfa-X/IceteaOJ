import pytest
from pydantic import ValidationError

from app.languages import (
    LanguageAlreadyExistsError,
    LanguageNotFoundError,
    LanguageRegistry,
)
from app.models import LanguageConfig


def test_registry_has_default_languages():
    registry = LanguageRegistry()

    assert registry.list_languages() == ["cpp", "python"]

    python_config = registry.get_language("python")
    assert python_config.name == "python"
    assert python_config.file_ext == ".py"
    assert python_config.run_cmd == "python {src}"

    cpp_config = registry.get_language("cpp")
    assert cpp_config.name == "cpp"
    assert cpp_config.file_ext == ".cpp"
    assert cpp_config.compile_cmd == "g++ {src} -o {exe}"
    assert cpp_config.run_cmd == "{exe}"


def test_registry_registers_new_language():
    registry = LanguageRegistry()

    registry.register_language(
        LanguageConfig(
            name="go",
            file_ext=".go",
            compile_cmd="go build -o {exe} {src}",
            run_cmd="{exe}",
            time_limit=3.0,
            memory_limit=128,
        )
    )

    assert registry.list_languages() == ["cpp", "go", "python"]
    assert registry.get_language("go").file_ext == ".go"


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
        registry.get_language("rust")


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