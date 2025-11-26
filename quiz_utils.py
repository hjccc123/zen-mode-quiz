"""Core parsing and normalization utilities for the quiz application."""
import re

# --- Regex Patterns for Option Parsing ---
# Pattern 1: A. / A、 / A: / A．with whitespace prefix
RE_OPTS_1 = re.compile(r'(^|\s)([A-Z])[.、:．;；]\s*(.*?)(?=\s+[A-Z][.、:．;；]|$)', re.DOTALL | re.MULTILINE)
# Pattern 2: (A) / A) format
RE_OPTS_2 = re.compile(r'(^|\s)\(?([A-Z])\)[.:]?\s*(.*?)(?=\s+\(?[A-Z]\)?[.:]?|$)', re.DOTALL | re.MULTILINE)
# Pattern 3: Compact format A.xxx B.xxx (no space between)
RE_OPTS_3 = re.compile(r'([A-Z])[.、:．;；](.*?)(?=[A-Z][.、:．;；]|$)', re.DOTALL | re.MULTILINE)
# Pattern 4: Newline-separated options (each option on a new line)
RE_OPTS_4 = re.compile(r'^([A-Z])[.、:．;；)）]?\s*(.+?)$', re.MULTILINE)
# Pattern 5: Space-separated without delimiter (e.g., "A选项一 B选项二")
RE_OPTS_5 = re.compile(r'(?:^|\s)([A-Z])([^\sA-Z]+?)(?=\s+[A-Z][^\sA-Z]|\s*$)', re.DOTALL)


def normalize_text(text):
    """Normalize text by converting full-width characters to half-width and stripping whitespace."""
    if text is None:
        return ""
    text = str(text).strip()
    # Convert full-width punctuation to half-width
    replacements = {
        '：': ':', '（': '(', '）': ')', '．': '.', 
        '；': ';', '，': ',', '【': '[', '】': ']',
        '　': ' '  # Full-width space
    }
    for full, half in replacements.items():
        text = text.replace(full, half)
    return text


def normalize_answer(answer):
    """Normalize answer text to handle various formats."""
    if answer is None:
        return ""
    answer = str(answer).strip().upper()
    # Handle true/false variants
    true_values = {'对', '正确', 'TRUE', 'T', 'YES', 'Y', '是', '√', '✓', '1'}
    false_values = {'错', '错误', 'FALSE', 'F', 'NO', 'N', '否', '×', '✗', '0'}
    if answer in true_values:
        return 'A'
    if answer in false_values:
        return 'B'
    # Remove spaces and sort for multi-select answers
    answer = answer.replace(' ', '').replace(',', '').replace('，', '')
    return ''.join(sorted(set(answer)))


def parse_options_zen(text):
    """Parse question text to extract options. Returns (question_text, options_dict)."""
    text = normalize_text(text)
    if not text:
        return "", {}
    
    options = {}
    question_text = text
    patterns = [RE_OPTS_1, RE_OPTS_2, RE_OPTS_3, RE_OPTS_4, RE_OPTS_5]
    
    for idx, p in enumerate(patterns):
        matches = list(p.finditer(text))
        if len(matches) >= 2:
            temp_options = {}
            first_match_start = float('inf')
            valid_keys = set()
            
            for m in matches:
                if idx == 2:  # Pattern 3: compact format
                    key, val = m.group(1).upper(), m.group(2).strip()
                elif idx == 3:  # Pattern 4: newline-separated
                    key, val = m.group(1).upper(), m.group(2).strip()
                elif idx == 4:  # Pattern 5: space-separated without delimiter
                    key, val = m.group(1).upper(), m.group(2).strip()
                else:  # Pattern 1, 2
                    groups = m.groups()
                    key, val = groups[-2].upper(), groups[-1].strip()
                
                # Skip if key is duplicate or value is empty
                if key in valid_keys or not val:
                    continue
                    
                temp_options[key] = val
                valid_keys.add(key)
                if m.start() < first_match_start:
                    first_match_start = m.start()
            
            # Validate: ensure we have at least 2 valid options with consecutive keys (A, B, C...)
            if len(temp_options) >= 2:
                sorted_keys = sorted(temp_options.keys())
                # Check if keys are consecutive starting from A
                expected = ord('A')
                consecutive = True
                for k in sorted_keys:
                    if ord(k) != expected:
                        consecutive = False
                        break
                    expected += 1
                
                if consecutive:
                    return text[:first_match_start].strip(), temp_options
    
    return question_text, options
