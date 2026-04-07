from translator_bot.config import BotConfig, LanguagePair


def make():
    return BotConfig(
        language_pairs=[
            LanguagePair(source=["en", "es"], target="ko"),
            LanguagePair(source=["ko"], target="en"),
        ],
        bot_name="TranslatorBot",
        claude_model="claude-sonnet-4-5-20250929",
        language_labels={"en": "EN", "es": "ES", "ko": "KO"},
    )


def test_target_for_english():
    assert make().target_for("en") == "ko"


def test_target_for_spanish():
    assert make().target_for("es") == "ko"


def test_target_for_korean():
    assert make().target_for("ko") == "en"


def test_target_for_unknown():
    assert make().target_for("fr") is None


def test_label_fallback():
    assert make().label("fr") == "FR"
