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

# Recursive JSON grammar used by the v2 local structured-response envelope.
# Semantic validation against LocalResponseEnvelope still happens after decoding.
AGENT_RESPONSE_JSON_GBNF = r"""
root    ::= ws value ws
value   ::= object | array | string | number | "true" | "false" | "null"
object  ::= "{" ws (member (ws "," ws member)*)? ws "}"
member  ::= string ws ":" ws value
array   ::= "[" ws (value (ws "," ws value)*)? ws "]"
string  ::= "\"" chars "\""
chars   ::= ([^"\\] | "\\" ["\\/bfnrt] | "\\u" hex hex hex hex)*
number  ::= "-"? ("0" | [1-9] [0-9]*) ("." [0-9]+)? ([eE] [+-]? [0-9]+)?
hex     ::= [0-9a-fA-F]
ws      ::= [ \t\n\r]*
"""
