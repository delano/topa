# TOPA Ideas & Evaluation Log

This document tracks ongoing dialogue about TOPA evolution, structured for DRY iteration and quick feedback cycles.

## Current Status

**Implemented**: TOPA v0.3 with ExecutionContext, cross-language normalization, 66% token reduction
**Active**: Ideas evaluation for incremental improvements

---

## Idea: REST-Inspired Hypermedia Actions

**Date**: 2025-01-31  
**Status**: Under Evaluation  
**Complexity**: Medium

### Concept
Add hypermedia action links to TOPA output, inspired by REST HATEOAS, to provide contextual next-step commands for debugging.

### Problem Statement
Current TOPA tells you **what happened** but leaves you to figure out **what to do next**. LLMs suggest generic debugging steps without knowing exact framework syntax.

### Proposed Solution
```yaml
tests/user_auth.py:
  L42: login validation failed
    Test: should authenticate valid user
    _actions:
      rerun: "pytest tests/user_auth.py::test_should_authenticate_valid_user -v"
      debug: "pytest tests/user_auth.py::test_should_authenticate_valid_user --pdb"
      trace: "pytest tests/user_auth.py::test_should_authenticate_valid_user -s --tb=long"
```

### Benefits
- Eliminates command syntax guesswork
- Framework-agnostic action vocabulary
- Contextual relevance per failure type
- Enables workflow chaining

### Implementation Approach
1. Detect original test framework from execution context
2. Map failures to framework-specific rerun commands  
3. Generate actions based on failure type and available tooling
4. Include in v0.3 output with token budget awareness

### Evaluation Criteria
- Token overhead impact
- Cross-framework consistency
- Developer workflow improvement
- Integration complexity with existing parsers

### Next Steps
1. Prototype with tryouts `--agent` mode (ideal testbed)
2. Define standard action vocabulary
3. Implement in tpane v0.3 encoder
4. Gather feedback on utility vs complexity

---

## Template for Future Ideas

### Idea: [Title]

**Date**: YYYY-MM-DD  
**Status**: [Under Evaluation|Accepted|Rejected|Implemented]  
**Complexity**: [Low|Medium|High]

#### Concept
Brief description of the idea.

#### Problem Statement
What problem does this solve?

#### Proposed Solution
Technical approach with examples.

#### Benefits
Expected improvements.

#### Implementation Approach
Steps to implement.

#### Evaluation Criteria
How to measure success.

#### Next Steps
Immediate actions to take.

#### Decision Log
Track evaluation progress and decisions.

---

## Evaluation Guidelines

**Accept if**:
- Solves real pain point
- Maintains token efficiency
- Cross-language compatible
- Low implementation complexity

**Reject if**:
- Adds significant token overhead
- Framework-specific only  
- Complex implementation for marginal benefit
- Conflicts with existing v0.3 principles

**Defer if**:
- Good idea but timing unclear
- Requires broader ecosystem support
- Needs more validation data