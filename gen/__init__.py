"""Generation: retrieved chunks -> cited answer via the Anthropic API.

Owns Stages 6-7 (SPEC.md §4). Two hard rules live here: no claim without a
[page] citation, and low retrieval confidence returns "not in the filing"
rather than a guess (SPEC.md §2). Zero buy/sell/recommendation language,
including in the prompt (CLAUDE.md hard constraint).
"""
