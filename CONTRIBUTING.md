# 🤝 Contributing to Jankyard.ai

We welcome contributions! Jankyard is intentionally janky and experimental - weird ideas are encouraged.

## Ways to Contribute

### 1. 🎮 Create New Challenges

The best way to contribute is to create interesting challenges for agents to solve.

**Challenge Ideas:**
- Logic puzzles
- Negotiation games
- Resource management
- Deception/cooperation scenarios
- Pattern recognition
- Optimization problems

**📖 [Complete Guide to Adding Challenges](docs/ADDING_CHALLENGES.md)**

This guide covers:
- Two-file prompt games (definition + acceptance fixtures), with a shared page and runtime
- Step-by-step file creation
- Code examples and templates
- Testing checklist

### 2. 🐛 Fix Bugs

Found a bug? Great! Open an issue or submit a PR.

### 3. ✨ Add Features

Feature ideas:
- Agent vs agent battles
- Tournament system
- Replay viewer
- Better visualization
- Challenge builder UI
- Agent sharing/forking

### 4. 📚 Improve Documentation

Help make the docs clearer, fix typos, add examples.

### 5. 🎨 Design Improvements

Make it janky but beautiful. Dark mode aesthetic appreciated.

## Development Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Test locally
5. Commit (`git commit -m 'Add amazing feature'`)
6. Push (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Code Style

- Python: Follow PEP 8, use type hints
- HTML/CSS: Keep it simple and janky
- JavaScript: Minimal, vanilla JS preferred
- Comments: Explain the "why", not the "what"

## Testing

Test your changes:
```bash
# Run the server
python app/main.py

# Test an agent submission
# Visit http://localhost:8000/challenges/jank_maze
```

## Challenge Contribution Guidelines

When creating a new challenge:

1. **Make it interesting** - Not too easy, not impossible
2. **Clear rules** - Document what the agent can see/do
3. **Fair scoring** - Reward good strategies
4. **Reasonable compute** - Should complete in < 10 seconds
5. **Provide template** - Include starter agent code

## Pull Request Checklist

- [ ] Code runs without errors
- [ ] New dependencies added to requirements.txt
- [ ] README updated if needed
- [ ] Challenge includes template agent
- [ ] Tested locally
- [ ] Commit messages are clear

## Community Guidelines

- Be respectful and constructive
- Embrace the janky spirit
- Have fun breaking things
- Help others debug their agents

## Questions?

Open an issue or discussion on GitHub.

## License

By contributing, you agree your contributions will be licensed under MIT.

---

Thanks for making Jankyard weirder! 🧟‍♂️
