"""
WISPAR FLOW - Local AI Text Cleaner
Rule-based filler word removal, capitalization, and optional local Ollama cleanup.
100% offline & local - zero paid APIs.
"""

import re
import urllib.request
import json

FILLER_WORDS = [
    r'\b(um+)\b',
    r'\b(uh+)\b',
    r'\b(ah+)\b',
    r'\b(er+)\b',
    r'\b(hm+)\b',
    r'\b(like,?\s+){2,}',  # repeated 'like, like'
    r'\b(you know,?\s+)',  # 'you know' filler
]

CODING_RULES = [
    (r'\bequals equals\b', '=='),
    (r'\bnot equals\b', '!='),
    (r'\bgreater than or equal\b', '>='),
    (r'\bless than or equal\b', '<='),
    (r'\bgreater than\b', '>'),
    (r'\bless than\b', '<'),
    (r'\bfat arrow\b', '=>'),
    (r'\barrow\b', '->'),
    (r'\bopen brace\b|\bopen curly\b', '{'),
    (r'\bclose brace\b|\bclose curly\b', '}'),
    (r'\bopen bracket\b', '['),
    (r'\bclose bracket\b', ']'),
    (r'\bopen paren\b|\bopen parenthesis\b', '('),
    (r'\bclose paren\b|\bclose parenthesis\b', ')'),
]

MARKDOWN_RULES = [
    (r'\btask item\b|\btodo item\b', '- [ ] '),
    (r'\bcode block\b', '```'),
    (r'\binline code\b', '`'),
    (r'\bheader one\b', '# '),
    (r'\bheader two\b', '## '),
    (r'\bheader three\b', '### '),
]

class TextCleaner:
    def __init__(self, config_manager=None):
        self.config = config_manager

    def clean(self, text: str) -> str:
        if not text:
            return text

        if self.config and not self.config.get("cleaner_enabled", True):
            return text

        mode = self.config.get("dictation_mode", "general") if self.config else "general"

        # 1. Apply Mode-Specific Transformation
        if mode == "coding":
            text = self._apply_coding_mode(text)
        elif mode == "markdown":
            text = self._apply_markdown_mode(text)

        # 2. Remove Filler Words if enabled
        if self.config is None or self.config.get("remove_fillers", True):
            for filler_pat in FILLER_WORDS:
                text = re.sub(filler_pat, '', text, flags=re.IGNORECASE)

        # 3. Fix duplicate stuttered words (e.g. "the the" -> "the")
        text = re.sub(r'\b(\w+)\s+\1\b', r'\1', text, flags=re.IGNORECASE)

        # 4. Capitalize first letter of sentences (Skip for coding mode)
        if mode != "coding":
            text = self.capitalize_sentences(text)

        # 5. Clean up spaces
        text = re.sub(r'[ \t]+', ' ', text).strip()

        # 6. Optional local Ollama post-processing (if enabled by user)
        if self.config and self.config.get("ollama_enabled", False):
            text = self._clean_with_ollama(text)

        return text

    def _apply_coding_mode(self, text: str) -> str:
        # Casing transformations: snake case <phrase>, camel case <phrase>, pascal case <phrase>
        def snake_repl(m):
            words = m.group(1).strip().split()
            return "_".join(w.lower() for w in words)

        def camel_repl(m):
            words = m.group(1).strip().split()
            if not words: return ""
            return words[0].lower() + "".join(w.capitalize() for w in words[1:])

        def pascal_repl(m):
            words = m.group(1).strip().split()
            return "".join(w.capitalize() for w in words)

        text = re.sub(r'\bsnake case ([a-zA-Z0-9\s]+?)(?=[.,!?]|$)', snake_repl, text, flags=re.IGNORECASE)
        text = re.sub(r'\bcamel case ([a-zA-Z0-9\s]+?)(?=[.,!?]|$)', camel_repl, text, flags=re.IGNORECASE)
        text = re.sub(r'\bpascal case ([a-zA-Z0-9\s]+?)(?=[.,!?]|$)', pascal_repl, text, flags=re.IGNORECASE)

        for pat, repl in CODING_RULES:
            text = re.sub(pat, repl, text, flags=re.IGNORECASE)
        return text

    def _apply_markdown_mode(self, text: str) -> str:
        for pat, repl in MARKDOWN_RULES:
            text = re.sub(pat, repl, text, flags=re.IGNORECASE)
        return text

    def capitalize_sentences(self, text: str) -> str:
        """Capitalize first character of text and after punctuation mark followed by space."""
        if not text:
            return text
        
        # Capitalize start
        text = text[0].upper() + text[1:]
        
        def cap_match(m):
            return m.group(1) + m.group(2).upper()
            
        return re.sub(r'([.!?]\s+)([a-z])', cap_match, text)

    def _clean_with_ollama(self, text: str) -> str:
        """Post-process text using local Ollama model if running."""
        try:
            url = self.config.get("ollama_url", "http://localhost:11434") + "/api/generate"
            model = self.config.get("ollama_model", "llama3")
            prompt = f"Fix spelling and grammar of this transcript. Output ONLY the polished text with no explanations:\n\n{text}"
            
            req = urllib.request.Request(
                url,
                data=json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                cleaned = res.get("response", "").strip()
                if cleaned:
                    return cleaned
        except Exception:
            pass  # Fall back silently to rule-based output if Ollama is not running locally
        return text
