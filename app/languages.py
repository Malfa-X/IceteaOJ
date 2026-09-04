from app.models import LanguageConfig


class LanguageNotFoundError(Exception):
    pass


class LanguageAlreadyExistsError(Exception):
    pass


class LanguageRegistry:
    def __init__(self):
        self._languages: dict[str, LanguageConfig] = {}

        self.register_language(
            LanguageConfig(
                name="python",
                file_ext=".py",
                run_cmd="python {src}",
                time_limit=3.0,
                memory_limit=128,
            )
        )
        self.register_language(
            LanguageConfig(
                name="cpp",
                file_ext=".cpp",
                compile_cmd="g++ {src} -o {exe}",
                run_cmd="{exe}",
                time_limit=3.0,
                memory_limit=128,
            )
        )

    def list_languages(self) -> list[str]:
        return sorted(self._languages.keys())

    def get_language(self, name: str) -> LanguageConfig:
        if name not in self._languages:
            raise LanguageNotFoundError(name)

        return self._languages[name]

    def register_language(self, language: LanguageConfig) -> None:
        if language.name in self._languages:
            raise LanguageAlreadyExistsError(language.name)

        self._languages[language.name] = language