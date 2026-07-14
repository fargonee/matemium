"""GBNF (GGML BNF) grammar templates for constraining local GGUF generation (llama-cpp-agent pattern)."""

from __future__ import annotations

# GBNF grammar to force the local model to output strictly one or more Aider SEARCH/REPLACE blocks.
# This prevents smaller models (e.g., Qwen-3B) from leaking conversational prose or raw markdown wraps.
AIDER_DIFF_GBNF = r"""
root         ::= block+
block        ::= "<<<<<<< SEARCH\n" content "=======\n" content ">>>>>>> REPLACE\n"
content      ::= line*
line         ::= [^\n]* "\n"
"""

# GBNF grammar to force the local model to output standard JSON matching a simple key-value structure.
SIMPLE_JSON_GBNF = r"""
root   ::= object
object ::= "{\n" space ( pair ( ",\n" space pair )* )? "\n}"
pair   ::= string ":" space value
string ::= "\"" [^\"]* "\""
value  ::= string | number | "true" | "false" | "null"
number ::= [0-9]+ ( "." [0-9]+ )?
space  ::= "  " | ""
"""
