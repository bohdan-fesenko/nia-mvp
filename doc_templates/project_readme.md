# Project Documentation Guide: [Project Name]

This directory contains all documentation for the [Project Name] project, organized to support the software development lifecycle with AI copilots. The documentation is structured to facilitate planning, design, implementation, and tracking throughout the project.

## Directory Structure

```
project_docs/
│
├── README.md                     # This guide
│
├── project/                      # Core project documentation
│   ├── project_charter.md        # Project vision, objectives, scope, and constraints
│   ├── srs.md                    # System Requirements Specification
│   ├── add.md                    # Architecture Design Document
│   ├── cs.md                     # Coding Standards
│   ├── dsd.md                    # Database Schema Document
│   ├── apid.md                   # API Documentation
│   ├── ded.md                    # Development Environment Document
│   └── prd.md                    # Product Requirements Document
│
├── design/                       # Design documentation (if applicable)
│   ├── urd.md                    # User Research Document
│   ├── dsys.md                   # Design System
│   ├── wf.md                     # Wireframes
│   ├── uik.md                    # UI Kit
│   ├── hfp.md                    # High-Fidelity Prototypes
│   └── dig.md                    # Design Implementation Guide
│
├── features/                     # Feature-specific documentation
│   ├── core/                     # Core project setup feature
│   │   ├── fsp.md                # Feature Specification
│   │   └── tdd.md                # Technical Design Document
│   │
│   ├── [feature1]/               # Documentation for Feature 1
│   │   ├── fsp.md                # Feature Specification
│   │   └── tdd.md                # Technical Design Document
│   │
│   └── [feature2]/               # Documentation for Feature 2
│       ├── fsp.md                # Feature Specification
│       └── tdd.md                # Technical Design Document
│
├── tasks/                        # Task-specific documentation
│   ├── [feature1]/               # Tasks for Feature 1
│   │   ├── T001_[task_name].md   # Task Definition
│   │   └── T002_[task_name].md   # Task Definition
│   │
│   └── [feature2]/               # Tasks for Feature 2
│       └── T011_[task_name].md   # Task Definition
│
└── progress/                     # Progress tracking documentation
    ├── project_status.md         # Overall project status
    ├── feature_status.md         # Feature-level progress
    ├── bugs_tracker.md           # Bug tracking, analysis, and resolution
    ├── risk_register.md          # Project risk tracking
    ├── documentation_sync_review.md # Documentation synchronization status
    └── tasks/                    # Task tracking cards
        ├── task_card_T001.md     # Task Tracking Card for Task 1
        └── task_card_T002.md     # Task Tracking Card for Task 2
```

## Document Types

### Planning Documents (`project/`)
- **Project Charter**: Defines the project vision, objectives, stakeholders, success criteria, constraints, and high-level timeline
- **SRS**: Details the functional and non-functional requirements of the system
- **ADD**: Describes the system architecture, technology stack, component architecture, data flow, security architecture, and deployment architecture
- **CS**: Outlines the coding conventions, naming standards, and best practices for the project
- **DSD**: Defines the database structure, tables, relationships, and optimization strategies
- **APID**: Details the API endpoints, request/response formats, authentication, and versioning strategy
- **DED**: Provides instructions for setting up the development environment, configuration files, and common issues
- **PRD**: Describes the product from a business and user perspective, including user personas, journeys, and feature requirements

### Design Documents (`design/`)
- **URD**: Documents user personas, journeys, and research findings
- **DSYS**: Defines design principles, color palette, typography, spacing, and grid systems
- **WF**: Creates low-fidelity interface layouts and user flows
- **UIK**: Specifies reusable UI components with usage guidelines
- **HFP**: Provides detailed visual designs and interactive prototypes
- **DIG**: Offers technical guidance for developers on implementing designs

### Feature Documents (`features/`)
- **FSP**: Feature Specification - defines the scope, requirements, and acceptance criteria for a specific feature
- **TDD**: Technical Design Document - provides the technical implementation details, architecture, and data models for a specific feature

### Task Documents (`tasks/`)
- **TD**: Task Definition - defines a specific implementation task, including description, acceptance criteria, implementation steps, and testing instructions

### Progress Tracking (`progress/`)
- **Project Status**: Provides an executive overview of the entire project status, including milestones, blockers, and metrics
- **Feature Status**: Tracks the status of features with cross-feature and cross-task dependencies
- **Bugs Tracker**: Manages bug reports, analysis, resolution status, and lessons learned from bug fixes
- **Risk Register**: Tracks identified risks, their severity, mitigation strategies, and contingency plans
- **Documentation Sync Review**: Ensures documentation stays in sync with implementation
- **Task Card**: Contains detailed progress information for individual tasks with dependencies

## Document Dependencies

Documents have specific dependencies that should be respected:
- Feature Specifications depend on the Product Requirements Document
- Technical Design Documents depend on Feature Specifications and the Architecture Design Document
- Task Definitions depend on Technical Design Documents and Feature Specifications
- Design Implementation Guide depends on High-Fidelity Prototypes
- UI Kit depends on the Design System
- Documentation Sync Review depends on Task Definitions
- Bug Tracker entries depend on Task Cards for related tasks

## How to Use This Documentation

1. **For Project Overview**: Start with the Project Charter and SRS in the `project/` directory
2. **For Technical Details**: Refer to the ADD, DSD, and APID in the `project/` directory
3. **For Design Guidelines**: Review the Design System and Design Implementation Guide in the `design/` directory
4. **For Feature Implementation**: Check the feature specifications in the `features/` directory and the task definitions in the `tasks/` directory
5. **For Progress Tracking**: Review the documents in the `progress/` directory
6. **For Lessons Learned**: Explore the bug resolution sections in the bugs_tracker.md file

## Document Naming Conventions

- Project-level documents: `document_type.md` (e.g., `srs.md`)
- Design documents: `document_type.md` (e.g., `dsys.md`)
- Feature documents: `document_type.md` (e.g., `fsp.md`) within feature-specific folders
- Task documents: `T{task_id}_[task_name].md` (e.g., `T001_[task_name].md`)
- Progress tracking documents: `document_type.md` (e.g., `feature_status.md`)
- Task cards: `task_card_T{task_id}.md` (e.g., `task_card_T001.md`)

## Document Templates

Document templates are stored in the `doc_templates/` directory at the project root, organized by mode:
- `doc_templates/planning_mode/` - Templates for planning documents:
  - `project_charter.md` - Project Charter template
  - `srs.md` - System Requirements Specification template
  - `add.md` - Architecture Design Document template
  - `cs.md` - Coding Standards template
  - `dsd.md` - Database Schema Document template
  - `apid.md` - API Documentation template
  - `ded.md` - Development Environment Document template
  - `prd.md` - Product Requirements Document template

- `doc_templates/design_mode/` - Templates for design documents:
  - `urd.md` - User Research Document template
  - `dsys.md` - Design System template
  - `wf.md` - Wireframes template
  - `uik.md` - UI Kit template
  - `hfp.md` - High-Fidelity Prototypes template
  - `dig.md` - Design Implementation Guide template

- `doc_templates/feature_plan_mode/` - Templates for feature documents:
  - `fsp.md` - Feature Specification template
  - `tdd.md` - Technical Design Document template
  - `task.md` - Task Definition template

- `doc_templates/progress_tracking_mode/` - Templates for progress tracking:
  - `project_status.md` - Project Status Dashboard template
  - `feature_status.md` - Feature Status Tracker template
  - `bugs_tracker.md` - Bug Tracker template
  - `risk_register.md` - Risk Register template
  - `documentation_sync_review.md` - Documentation Sync Review template
  - `task_card.md` - Task Tracking Card template

- `doc_templates/bug_fixing_mode/` - Templates for bug documentation:
  - `bug.md` - Bug Report template
  - `ba.md` - Bug Analysis template

- `doc_templates/refactoring_mode/` - Templates for refactoring documentation:
  - `req.md` - Refactoring Request template
  - `ra.md` - Refactoring Analysis template

These templates should be used when creating new documentation to ensure consistency.

## Maintenance

All documentation should be kept up-to-date as the project evolves. After completing tasks, use the Documentation Synchronization process to update affected documents.

## Current Project Status

The project is currently in the [development phase]. The [Feature Name] (F00X) feature is in progress, with the following tasks completed:

1. T00X - [Task Name]: [Brief description of what was accomplished]
2. T00Y - [Task Name]: [Brief description of what was accomplished]

The next task in progress is T00Z - [Task Name].