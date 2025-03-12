# Feature Status Tracker: [Project Name]

## Feature Progress Summary

| Feature ID | Feature Name | Status | Progress | Tasks Complete | Tests Passing | Priority | Owner |
|-----------|--------------|--------|----------|----------------|---------------|----------|-------|
| F001 | [Feature 1] | [Planning/In Progress/Testing/Complete] | [X%] | [X/Y] | [X/Y] | [High/Medium/Low] | [Name] |
| F002 | [Feature 2] | [Planning/In Progress/Testing/Complete] | [X%] | [X/Y] | [X/Y] | [High/Medium/Low] | [Name] |

## Cross-Feature Dependencies

```mermaid
graph TD
    F001[Feature 1] --> F003[Feature 3]
    F002[Feature 2] --> F003
    F003 --> F004[Feature 4]
    
    %% Critical path highlighting
    classDef critical fill:#ffcccc,stroke:#ff0000,stroke-width:2px
    class F001,F003,F004 critical
```

## Detailed Feature Status

### Feature: [Feature 1] (F001)
- **Owner**: [Name]
- **Status**: [Planning/In Progress/Testing/Complete]
- **Start Date**: [Date]
- **Target Completion**: [Date]
- **Actual Completion**: [Date]
- **Dependencies**: [List of features this feature depends on]
- **Dependents**: [List of features that depend on this feature]

#### Documentation:
- [Link to Feature Specification]
- [Link to Technical Design Document]

#### Progress:
- Requirements: [X%]
- Design: [X%]
- Implementation: [X%]
- Testing: [X%]

#### Cross-Task Dependencies

```mermaid
graph TD
    T001[Task 1: Setup API] --> T002[Task 2: Implement UI]
    T001 --> T003[Task 3: Create Tests]
    T002 --> T004[Task 4: Integration]
    T003 --> T004
    
    %% Task status styling
    classDef done fill:#d4edda,stroke:#28a745
    classDef inProgress fill:#fff3cd,stroke:#ffc107
    classDef todo fill:#f8f9fa,stroke:#6c757d
    classDef blocked fill:#f8d7da,stroke:#dc3545
    
    class T001 done
    class T002 inProgress
    class T003 todo
    class T004 blocked
```

#### Task Status:

| Task ID | Description | Status | Assigned To | Dependencies | Blockers |
|---------|-------------|--------|-------------|--------------|----------|
| T001 | [Task description] | [Todo/In Progress/Done] | [Name] | [None/Task IDs] | [None/Description] |
| T002 | [Task description] | [Todo/In Progress/Done] | [Name] | [None/Task IDs] | [None/Description] |