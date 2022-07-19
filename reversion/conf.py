from dataclasses import dataclass


@dataclass
class Settings:
    REVERSION_SAVE_DELETE_EVENTS: bool
    REVERSION_REQUEST_METHODS: tuple[str]
    
    @classmethod
    def default(cls):
        return cls(
            REVERSION_SAVE_DELETE_EVENTS=True,
            REVERSION_REQUEST_METHODS=("OPTIONS", "HEAD", "TRACE"),
        )

    def load_from_settings(self):
        from django.conf import settings

        for setting_name in vars(self):
            try:
                value = getattr(settings, setting_name)
                setattr(self, setting_name, value)
            except AttributeError:
                pass


settings = Settings.default()

