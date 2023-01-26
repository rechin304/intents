"""Generate a summary for the website."""
from __future__ import annotations

import json

import yaml

from .const import INTENTS_FILE, LANGUAGES, LANGUAGES_FILE
from .util import load_merged_responses, load_merged_sentences


def run() -> int:
    language_summaries = []

    language_info = yaml.safe_load(LANGUAGES_FILE.read_text())

    # Sort intent info by (domain, intent)
    intent_info = yaml.safe_load(INTENTS_FILE.read_text())

    # Collect all English responses.
    all_english_responses = {
        intent_sentence
        for intent_sentences in load_merged_responses("en")["responses"][
            "intents"
        ].values()
        for intent_sentence in intent_sentences.values()
    }

    for language in LANGUAGES:
        merged_sentences = load_merged_sentences(language)
        merged_responses = load_merged_responses(language)

        intent_sentence_count = {intent: 0 for intent in intent_info}
        used_responses_per_intent: dict[str, set[str]] = {
            intent: set() for intent in intent_info
        }

        for intent, info in merged_sentences["intents"].items():
            for sentence_set in info["data"]:
                intent_sentence_count[intent] += len(sentence_set["sentences"])
                used_responses_per_intent.setdefault(intent, set()).add(
                    sentence_set.get("response", "default")
                )

        response_sentence_count = {intent: 0 for intent in intent_info}
        intent_responses_translated: dict[str, bool] = {}

        for intent, intent_responses in merged_responses["responses"][
            "intents"
        ].items():
            response_sentence_count.setdefault(intent, 0)
            response_sentence_count[intent] += len(intent_responses)

            if language == "en":
                intent_responses_translated[intent] = True
            else:
                intent_responses_translated[intent] = all(
                    response not in all_english_responses
                    for response in intent_responses.values()
                )

        errors_translated = not any(
            translation.startswith("TODO ")
            for translation in merged_sentences["responses"]["errors"].values()
        )

        usable = (
            all(value > 0 for value in intent_sentence_count.values())
            and all(len(value) > 0 for value in used_responses_per_intent.values())
            and errors_translated
            and all(intent_responses_translated.values())
        )

        # Turn set into count
        used_responses_count = {
            intent: len(response_set)
            for intent, response_set in used_responses_per_intent.items()
        }

        language_summaries.append(
            {
                "language": language,
                "native_name": language_info[language]["nativeName"],
                "leaders": language_info[language].get("leaders"),
                "intents": intent_sentence_count,
                "used_responses": used_responses_count,
                "responses": response_sentence_count,
                "intent_responses_translated": intent_responses_translated,
                "errors_translated": errors_translated,
                "usable": usable,
            }
        )

    intents = {}
    for intent, info in intent_info.items():
        intents[intent] = {
            "file_name": f"{info['domain']}_{intent}.yaml",
        }

    print(
        json.dumps(
            {
                "intents": intents,
                "languages": language_summaries,
            },
            indent=2,
        )
    )

    return 0
