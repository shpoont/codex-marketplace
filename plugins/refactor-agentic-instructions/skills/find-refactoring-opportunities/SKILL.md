---
name: find-refactoring-opportunities
description: Find worthwhile refactoring opportunities in AI agent or local assistant instructions without changing them.
---

Find worthwhile refactoring opportunities in the instructions for the target identified in the user's request and propose changes for the user to select.

Resolve the target using host or project evidence, including app identity when needed, before choosing how to access its instructions. For a whole setup, review relevant global/project guidance, skills, plugins, and references. Prefer available source files or configuration; clarify material ambiguity and state coverage gaps.

Look for improvements to clarity and maintainability that preserve intended behavior, requirements, and useful context.

Briefly describe each opportunity, where it applies, and why it is worth doing. Distinguish behavior-preserving refactoring opportunities from existing defects and unresolved policy choices. Identify anything you could not verify.

Leave the target instructions unchanged; do not execute the workflows they describe.
