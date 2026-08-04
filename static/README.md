# AuthorLite Flask - Small-Scale Writing Assistant

## Overview

AuthorLite is a Python Flask application inspired by the TypeScript [AuthorAgent](https://github.com/Ckokoski/AuthorAgent), optimized for smaller-scale writing projects, smaller local LLM model contexts. Currently designed to work with LM Studio.  

### Key Features
- 📖 Story permise generation with multiple structure templates
- ✨ Chapter writing with review and polishing
---

## Quick Start Guide



## Quality Checking

The application performs comprehensive quality checks on each chapter:

- **Word Count Validation**: 500-3000 words target range
- **Character Voice Consistency**: Analyzes vocabulary per character
- **Emotional Arc Depth**: Evaluates progression and transitions
- **Continuity Checks**: Verifies consistency with established characters

---


### .env.example

Copy to `.env` and customize:

```bash
cp .env.example .env
nano .env           # Edit with your settings
```

## Acknowledgments

Based on the AuthorAgent TypeScript application, adapted to Python Flask with:
- Self-hosted model-only architecture (zero external API costs)
- Enhanced error handling with recovery guidance patterns
- Built-in manuscript reader component
- Persistent volume support for production deployments
