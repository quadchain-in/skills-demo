---
name: auto-push
description: >-
  Use this skill to automatically stage, commit, and push changes in the skills_demo repository.
---

# Auto Git Push Skill

This skill automates the process of committing and pushing your code changes to the remote repository.

## Steps to Execute

1. **Check Git Status:**
   - Run `git status` inside the `skills_demo` directory to identify modified, added, or deleted files.

2. **Stage Changes:**
   - Run `git add .` to stage all changes.

3. **Generate a Commit Message:**
   - Review the staged changes (e.g., using `git diff --cached`).
   - Generate a concise and descriptive commit message explaining the updates.
   - Run `git commit -m "<your_generated_message>"`.

4. **Push to Remote:**
   - Run `git push origin main` (or the appropriate branch name) to push the commit to the remote repository.

5. **Verify:**
   - Confirm that the push was successful and report the summary of the commit to the user.
