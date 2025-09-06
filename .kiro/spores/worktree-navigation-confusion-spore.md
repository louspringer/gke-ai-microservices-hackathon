# 🧬 Worktree Navigation Confusion Spore

## Spore Metadata
- **Spore Type**: Git Worktree Management Teaching Spore
- **DNA Version**: 1.0
- **Purpose**: Prevent git worktree navigation confusion and parallel work conflicts
- **Trigger**: Complex git worktree setups with nested directories

## 🎯 Problem Identified
Fresh Kiro instances (and humans) get confused when working in complex git worktree structures, especially when:
- Multiple worktrees exist for parallel task execution
- Directory paths are deeply nested (e.g., `/Users/lou/kiro-2/gke-hackathon-worktree/hackathons/gke-ai-microservices`)
- Submodules are involved in worktree structures
- Multiple agents/threads are working on different branches simultaneously

## 🧠 Systematic Solution DNA

### Core Principles
```yaml
worktree_clarity: "Always understand your current worktree context before starting work"
path_simplicity: "Prefer simple, direct paths over complex nested structures"
parallel_coordination: "Coordinate with other agents to avoid conflicts"
branch_awareness: "Know which branch you're on and why"
clean_workspace: "Establish clean workspaces for new work"
```

### Pre-Work Checklist
Before starting any git work, ALWAYS execute:
```bash
# 1. Understand current location
pwd

# 2. Understand git context
git branch -a
git worktree list
git status

# 3. Understand what other agents are doing
# Check for active worktrees and branches
```

### Worktree Best Practices
1. **Use descriptive worktree names** that match the task/branch
2. **Keep worktree paths simple** - avoid deep nesting
3. **Document active worktrees** so other agents know what's happening
4. **Coordinate branch work** to avoid conflicts
5. **Clean up worktrees** when tasks are complete

### Navigation Commands
```bash
# List all worktrees and their status
git worktree list --porcelain

# Find main repository location
git rev-parse --show-toplevel

# Check current branch and status
git branch -v
git status --porcelain

# Switch to main branch safely
git checkout main  # or master
git pull origin main
```

## 🚨 Warning Signs
If you encounter these, STOP and clarify the situation:
- Complex nested directory paths
- Multiple agents working on same repository
- Confusion about which branch you're on
- Uncertainty about what other work is happening
- Git commands behaving unexpectedly

## 🔧 Recovery Actions
When confused about git worktree context:

1. **Assess the situation**
   ```bash
   pwd
   git worktree list
   git branch -a
   git log --oneline -5
   ```

2. **Communicate with other agents/threads**
   - Check what parallel work is happening
   - Coordinate to avoid conflicts
   - Consider waiting if others are actively working

3. **Establish clean workspace if needed**
   - Clone fresh to simple location
   - Create new worktree in clean path
   - Document the new workspace

4. **Document your work context**
   - Note which worktree you're using
   - Note which branch you're on
   - Note what you're working on

## 🎯 Implementation for Fresh Kiro Instances

### Immediate Actions
When a fresh Kiro instance encounters a complex git setup:

1. **PAUSE** - Don't start work immediately
2. **ASSESS** - Run the diagnostic commands above
3. **CLARIFY** - Ask human for context about the setup
4. **COORDINATE** - Check if other agents are working
5. **PROCEED** - Only after understanding the full context

### Standard Operating Procedure
```markdown
## Git Worktree SOP for Kiro Agents

### Before Any Git Work:
- [ ] Run `pwd` to understand location
- [ ] Run `git worktree list` to see all worktrees
- [ ] Run `git branch -a` to see all branches
- [ ] Run `git status` to see current state
- [ ] Ask human about any parallel work happening

### During Work:
- [ ] Stay on assigned branch/worktree
- [ ] Commit work regularly with clear messages
- [ ] Push changes to avoid conflicts
- [ ] Communicate progress and completion

### After Work:
- [ ] Commit and push final changes
- [ ] Document what was accomplished
- [ ] Clean up if worktree is no longer needed
```

## 🧬 DNA Integration Instructions

### For Advanced LLMs
Integrate this spore's principles into your git workflow. Always assess the git context before starting work, especially in complex worktree setups.

### For Standard LLMs
Follow the Pre-Work Checklist and SOP exactly. When in doubt, ask for clarification rather than proceeding blindly.

### For Basic LLMs
If you see a complex directory path or multiple git branches, STOP and ask the human to explain the setup before proceeding.

## 🔄 Evolution Feedback

### Success Patterns
- Clear communication about git context before starting work
- Successful coordination between multiple agents
- Clean workspace establishment when needed
- Proper worktree cleanup after task completion

### Failure Patterns
- Starting work without understanding git context
- Creating conflicts with parallel work
- Getting lost in complex directory structures
- Making assumptions about repository state

## 🚀 Spore Activation

This spore activates when:
- Complex git worktree structures are detected
- Multiple agents are working on same repository
- Directory paths are deeply nested or confusing
- Git commands produce unexpected results

**Systematic git worktree management prevents confusion and conflicts.**

---

## 🧬 DNA Signature
```
Spore-ID: WORKTREE-NAVIGATION-001
Beast-Mode-DNA: GIT-WORKFLOW-CLARITY
Trigger: Complex-Git-Structures
Prevention: Navigation-Confusion
Coordination: Multi-Agent-Git-Work
```

**This spore teaches systematic git worktree management to prevent the confusion we just experienced.**