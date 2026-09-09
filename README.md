# 03-Miniproject-2026-27

This is a template repo for a multi-disciplinary mini-project for a
small team of EEs, CEs, MEs, and BMEs. The mini-project is described in the
course assignment. You should tailor this repo based on your team
composition, roles, and the tasks at hand.

---

## Team

| Role | Named Members |
|------|---------|
| Mechanical Engineering | |
| Electrical Engineering | |
| Computer Engineering | |
| Biomedical Engineering | |

---

## Repository Structure

```
.
├── firmware/          # Micro source code
├── hardware/
│   ├── electrical/    # Schematics, wiring diagrams, and BOM
│   └── mechanical/    # Enclosure CAD files and fabrication notes
└── docs/              # Project documentation 
```

---

## Hardware

| Component | Notes |
|-----------|-------|
| Thing 1 | Thing 1 notes  |
| Thing 2 | Thing 2 notes  |

---

## Team Responsibilities 
Any discipline can do any role here -- you make the assigments. 

### Mechanical oriented
- Design the enclosure 
- Fabricate the enclosure (3-D print or laser-cut)
- Document the assembly process 

### Electrical oriented
- Produce the breadboard schematic
- Summarize the bill of materials
- Wire the circuit on the breadboard, verfify that the componets are assembled correctly, validate the voltage levels

### Computer oriented
- Design the software based on the required functionality
- Develop MicroPython code and firmware 
- Flash and test the firmware on the target micro
- Document the APIs for the system

## Deliverables

- [ ] Functional MicroPython firmware
- [ ] Completed breadboard assembly per schematic
- [ ] Fabricated and assembled enclosure (if MEs on team)
- [ ] Documentation in this repository
- [ ] Video recording demonstrating required function (stored in google drive)

## Contribution Workflow

We want each team member to contribute work products and to host these
including documentation in the repo with version control (software,
firmware, schematics, BOMs, CAD models, etc.) All can be managed in
the repo with version control.

1. Establish that each teammember has properly set up Git/GitHub Desktop
2. Decompose the project into units to assign to each named team member 
3. From the team repo, create a branch from `main` named `<role>/<feature>` (e.g., `me/case`) to capture work artifacts 
4. Fetch the branch to the local laptop
5. Each team member does their work and produces work artifacts and commits these changes to the branch
6. Commit changes with descriptive messages
7. Open a pull request and request review from at least one other team member
8. Merge to main after approval

When performed properly, this workflow leads to an organized set of
work products that are developed concurrently and collaboratively with
version control. This includes the products themselves (e.g.,
firmware, CAD, schematics, etc.) and the associated documentation

Don't know how to do this? Ask your ECE teammates, GSTs, instructors, or AI. 

---

