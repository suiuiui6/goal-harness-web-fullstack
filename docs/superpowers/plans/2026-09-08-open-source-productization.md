# Open-Source Productization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Package Goal Harness as a clear, runnable, trustworthy open-source project.

**Architecture:** Add a thin Python CLI that delegates to the existing Goal, Harness, and Guard entry points. Add repository-level documentation and GitHub automation without changing delivery state semantics.

**Tech Stack:** Python 3.11+, argparse, pytest, GitHub Actions, Markdown.

---

### Task 1: Product CLI

- [ ] Write failing tests for help, validate, capability-check, and delivery-audit.
- [ ] Implement `goal_harness/__main__.py` as a subprocess orchestration layer.
- [ ] Run `python -B -m pytest tests/test_product_cli.py -q` and require pass.

### Task 2: Public Documentation

- [ ] Add bilingual `README.md`, `LICENSE`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, and release notes.
- [ ] Add a documentation contract test checking quick start, evidence limits, Windows wording, license, and contribution links.
- [ ] Run the documentation test and link checker.

### Task 3: GitHub Project Infrastructure

- [ ] Add CI, issue forms, pull request template, and dependabot configuration.
- [ ] Validate YAML and required workflow commands without adding dependencies.
- [ ] Run the full clean-shell candidate regression.

### Task 4: Publish

- [ ] Scan tracked files for likely credentials and excluded governance state.
- [ ] Commit and push productization changes.
- [ ] Set description, topics, homepage, and public visibility.
- [ ] Create and verify signed-off `v0.1.0` release metadata.
