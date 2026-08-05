import re
import unicodedata
from dataclasses import dataclass


MAX_LINE_CHARS = 120
USE_TWO_CHARACTER_ALTERNATION = True

MARKDOWN_TO_RENPY = [
    (r"\*\*\*(.+?)\*\*\*", r"{b}{i}\1{/i}{/b}"),
    (r"___(.+?)___", r"{b}{i}\1{/i}{/b}"),
    (r"\*\*_(.+?)_\*\*", r"{b}{i}\1{/i}{/b}"),
    (r"__\*(.+?)\*__", r"{b}{i}\1{/i}{/b}"),
    (r"\*__(.+?)__\*", r"{b}{i}\1{/i}{/b}"),
    (r"_\*\*(.+?)\*\*_", r"{b}{i}\1{/i}{/b}"),
    (r"\*\*(.+?)\*\*", r"{b}\1{/b}"),
    (r"__(.+?)__", r"{b}\1{/b}"),
    (r"\*(.+?)\*", r"{i}\1{/i}"),
    (r"_(.+?)_", r"{i}\1{/i}"),
]

RENPY_TO_MARKDOWN = [
    (r"\{b\}\{i\}(.+?)\{/i\}\{/b\}", r"***\1***"),
    (r"\{i\}\{b\}(.+?)\{/b\}\{/i\}", r"***\1***"),
    (r"\{b\}(.+?)\{/b\}", r"**\1**"),
    (r"\{i\}(.+?)\{/i\}", r"*\1*"),
]


@dataclass(frozen=True)
class TxtToRenpyConfig:
    header: str
    default_name: str
    default_id: str
    narrator_name: str
    narrator_id: str
    first_person: bool
    speaker: object
    spoken: object
    expression: object
    block: object


@dataclass(frozen=True)
class RenpyToTextConfig:
    restored_suffix: str
    generic_name: str
    format_dialogue: object


def esc(text):
    return text.replace("\\", "\\\\").replace('"', '\\"')


def unesc(text):
    return text.replace('\\"', '"').replace("\\\\", "\\")


def apply_replacements(text, replacements):
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text)
    return text


def markdown_to_renpy(text):
    return apply_replacements(text, MARKDOWN_TO_RENPY)


def renpy_to_markdown(text):
    return apply_replacements(text, RENPY_TO_MARKDOWN)


def slug(name, default_id):
    raw = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    ident = re.sub(r"\W+", "_", raw.lower()).strip("_") or default_id
    return f"p_{ident}" if ident[0].isdigit() else ident


def split_text(text, max_line_chars=MAX_LINE_CHARS):
    if len(text) <= max_line_chars:
        return [text]
    return [p.strip() for p in re.findall(r"[^.]+(?:\.|$)", text) if p.strip()] or [text]


def end_dialogue(text):
    text = text.rstrip()
    return text if text.endswith((".", "!", "?")) else text.rstrip(",;:") + "."


def text_before_attribution(text):
    return text[:-1] if text.endswith(".") and not text.endswith("...") else text


EN_VERBS = "said|replied|answered|asked|exclaimed|whispered|shouted|cried|muttered"
EN_PRONOUNS = "he|she|they|we|it|i|you"
EN_OPEN_QUOTES = ('"', "“", "``", "''")
EN_CLOSE_QUOTES = ('"', "”", "''", "\u00b4\u00b4")


def en_clean_name(name):
    name = re.sub(
        r"\b(with|without|while|when|because|but|and|calmly|quietly|softly|loudly|slowly)\b.*$",
        "",
        name.strip(" .,:;!?"),
    )
    name = re.sub(r"^(the|a|an)\s+", "", name, flags=re.I).strip()
    return name[:1].upper() + name[1:] if name else "Character"


def en_quote_marker(line):
    stripped = line.lstrip()
    return next((marker for marker in EN_OPEN_QUOTES if stripped.startswith(marker)), None)


def en_quoted_parts(line):
    stripped = line.lstrip()
    opening = en_quote_marker(stripped)
    if not opening:
        return None, "", False
    text = stripped[len(opening):]
    closing_positions = [(idx, marker) for marker in EN_CLOSE_QUOTES if (idx := text.find(marker)) != -1]
    if not closing_positions:
        return text.strip(), "", False
    close_index, closing = min(closing_positions)
    return text[:close_index].strip(), text[close_index + len(closing):].lstrip(" ,").strip(), True


def en_after_quote(line):
    _, tail, closed = en_quoted_parts(line)
    return tail if closed else ""


def en_speaker(line):
    tail = en_after_quote(line)
    if re.match(rf"i\s+(?:{EN_VERBS})(?:\b|\s)", tail, flags=re.I):
        return "Narrator"
    match = re.match(rf"(.+?)\s+(?:{EN_VERBS})(?:\b|\s)", tail, flags=re.I)
    if not match:
        return None
    name = en_clean_name(match.group(1))
    return None if name.lower() in EN_PRONOUNS or name == "Character" else name


def en_spoken(line):
    quote_text, _, _ = en_quoted_parts(line)
    if quote_text is not None:
        return quote_text
    return line[1:].strip() if line.startswith(("—", "-")) else None


def en_expression(line):
    match = re.search(r"\bwith\s+([^.—\"”]+)", en_after_quote(line), flags=re.I)
    if not match:
        return "normal"
    text = re.sub(r"^(a|an|the)\s+", "", match.group(1).lower().strip(" .,:;!?"))
    text = re.sub(r"[^a-zA-Z0-9_ ]+", "", text)
    text = re.sub(r"\s+", " ", text.strip(" .,:;!?")).strip()
    return text.replace(" ", "_") if text else "normal"


def en_block(lines, index):
    block = [lines[index]]
    _, _, quote_closed = en_quoted_parts(lines[index])
    index += 1
    while not quote_closed and index < len(lines):
        next_index = index
        while next_index < len(lines) and not lines[next_index]:
            next_index += 1
        if next_index >= len(lines) or not en_quote_marker(lines[next_index]):
            break
        block.append(lines[next_index])
        _, _, quote_closed = en_quoted_parts(lines[next_index])
        index = next_index + 1
    return block, index


def en_quote_for_attribution(text):
    return f'"{text}"' if text.endswith(("!", "?", "...")) else f'"{text},"'


def en_format_dialogue(speaker_id, text, chars, expression):
    text = text_before_attribution(text)
    name = chars[speaker_id]
    expression = expression.replace("_", " ") if expression else None
    if name.lower() == "narrator":
        return f"{en_quote_for_attribution(text)} I said"
    if name.lower() == "character":
        return f"{en_quote_for_attribution(text)} said with {expression}" if expression else f'"{text}"'
    suffix = f" with {expression}" if expression else ""
    return f"{en_quote_for_attribution(text)} {name} said{suffix}"


ES_VERBS_3P = "dijo|respondio|respondió|contesto|contestó|pregunto|preguntó|exclamo|exclamó|susurro|susurró|grito|gritó"
ES_VERBS_1P = "dije|respondi|respondí|conteste|contesté|pregunte|pregunté|exclame|exclamé|susurre|susurré|grite|grité"
ES_ACCENTS = "áéíóúÁÉÍÓÚñÑüÜ"
ES_CONTINUATION_MARKERS = ("\u00bb", "\u00c2\u00bb")


def es_clean_name(name):
    name = re.sub(r"\b(con|sin|mientras|cuando|porque|pero|y)\b.*$", "", name.strip(" .,:;!?¡¿"), flags=re.I)
    name = re.sub(r"^(el|la|los|las|un|una|unos|unas)\s+", "", name, flags=re.I).strip()
    return name[:1].upper() + name[1:] if name else "Personaje"


def es_is_continuation(line):
    return line.startswith(ES_CONTINUATION_MARKERS)


def es_continuation_text(line):
    for marker in ES_CONTINUATION_MARKERS:
        if line.startswith(marker):
            return line[len(marker):].strip()
    return line


def es_speaker(line):
    if es_is_continuation(line):
        line = es_continuation_text(line)
    if re.search(rf"[—-]\s*(?:{ES_VERBS_1P})(?:\b|\s)", line, flags=re.I):
        return "Narrador"
    match = re.search(rf"[—-]\s*(?:{ES_VERBS_3P})\s+([^.—-]+)", line, flags=re.I)
    name = es_clean_name(match.group(1)) if match else "Personaje"
    return name if name != "Personaje" else None


def es_spoken(line):
    if es_is_continuation(line):
        text = es_continuation_text(line)
    elif line.startswith(("—", "-")):
        text = line[1:].strip()
    else:
        return None
    cut = re.search(rf"\s*[—-]\s*(?:{ES_VERBS_1P}|{ES_VERBS_3P})(?:\b|\s)", text, flags=re.I)
    return text[:cut.start()].strip() if cut else text


def es_expression(line):
    match = re.search(r"\bcon\s+([^.—-]+)", line, flags=re.I)
    if not match:
        return "normal"
    text = re.sub(rf"[^a-zA-Z0-9{ES_ACCENTS}_ ]+", "", match.group(1).lower())
    text = re.sub(r"\s+", " ", text.strip(" .,:;!?¡¿")).strip()
    return f"con {text}" if text else "normal"


def es_block(lines, index):
    block = [lines[index]]
    index += 1
    while index < len(lines):
        next_index = index
        while next_index < len(lines) and not lines[next_index]:
            next_index += 1
        if next_index >= len(lines) or not es_is_continuation(lines[next_index]):
            break
        block.append(lines[next_index])
        index = next_index + 1
    return block, index


def es_format_dialogue(speaker_id, text, chars, expression):
    text = text_before_attribution(text)
    name = chars[speaker_id]
    if name.lower() == "narrador":
        return f"—{text} —dije"
    if name.lower() == "personaje":
        suffix = f" {expression}" if expression else ""
        return f"—{text} —dijo{suffix}" if suffix else f"—{text}"
    suffix = f" {expression}" if expression else ""
    return f"—{text} —dijo {name}{suffix}"


EN_TXT_CONFIG = TxtToRenpyConfig(
    header="# Automatically generated from rpy_txt_conversor.py",
    default_name="Character",
    default_id="character",
    narrator_name="Narrator",
    narrator_id="narrator",
    first_person=True,
    speaker=en_speaker,
    spoken=en_spoken,
    expression=en_expression,
    block=en_block,
)

ES_TXT_CONFIG = TxtToRenpyConfig(
    header="# Archivo generado automaticamente desde rpy_txt_conversor.py",
    default_name="Personaje",
    default_id="personaje",
    narrator_name="Narrador",
    narrator_id="narrador",
    first_person=True,
    speaker=es_speaker,
    spoken=es_spoken,
    expression=es_expression,
    block=es_block,
)

EN_RESTORE_CONFIG = RenpyToTextConfig("_restored", "Character", en_format_dialogue)
ES_RESTORE_CONFIG = RenpyToTextConfig("_restaurado", "Personaje", es_format_dialogue)
