# Skills Directory

This directory contains reusable skills that extend capabilities for specific domains and tasks.

## Available Skills

### skill-creator

The skill-creator provides comprehensive guidance for creating effective skills. Use this when you want to create a new skill or update an existing skill that extends capabilities with specialized knowledge, workflows, or tool integrations.

**Location:** `.github/skills/skill-creator/`

**Key files:**
- `SKILL.md` - Complete skill documentation and instructions
- `scripts/init_skill.py` - Initialize a new skill from template
- `scripts/package_skill.py` - Package a skill into distributable .skill file
- `scripts/quick_validate.py` - Validate skill structure and frontmatter
- `references/workflows.md` - Best practices for workflow patterns
- `references/output-patterns.md` - Best practices for output formatting

### sync-job-expert

The sync-job-expert provides expert guidance for creating, implementing, and troubleshooting Sync Jobs in the Frappe Tweaks framework. Use when working with Sync Job Types, Sync Job controllers, sync job enqueueing, debugging sync job issues, implementing sync logic, or understanding sync job lifecycle and hooks.

**Location:** `.github/skills/sync-job-expert/`

**Key file:**
- `SKILL.md` - Complete sync job framework documentation

**When to use:**
- Creating new Sync Job Types
- Implementing sync job controllers (Standard or Bypass mode)
- Enqueueing and configuring sync jobs
- Understanding sync job lifecycle, statuses, and hooks
- Troubleshooting sync job failures
- Implementing batch operations with multiple targets

**Quick start:**

```bash
# Navigate to the skills directory
cd .github/skills

# Create a new skill
/workspace/development/frappe-bench/env/bin/python skill-creator/scripts/init_skill.py my-new-skill --path .

# Validate a skill
/workspace/development/frappe-bench/env/bin/python skill-creator/scripts/quick_validate.py ./my-new-skill

# Package a skill
/workspace/development/frappe-bench/env/bin/python skill-creator/scripts/package_skill.py ./my-new-skill
```

**Note:** Use the bench virtual environment Python (`/workspace/development/frappe-bench/env/bin/python`) to ensure all dependencies are available.

For complete documentation, see `skill-creator/SKILL.md`.

## Adding New Skills

1. Use the skill-creator to initialize new skills
2. Place skill directories directly in the `.github/skills/` folder
3. Each skill should be self-contained with its own SKILL.md file
4. Follow the patterns documented in skill-creator

## License

Skills are licensed under Apache License 2.0 unless otherwise specified. See individual skill LICENSE.txt files for details.
