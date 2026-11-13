# Forge — Project Builder Agent

Forge turns an early project idea into a practical first-build plan. Describe the idea, audience, project type, experience level, and any constraints; Forge creates a focused sequence of milestones, suggests a starter stack, drafts a few project files, and runs a small planning checklist.

Forge is a lightweight, local-first prototype. It runs in the browser without an API key, and saves recent plans in that browser's local storage.

## Features

- Guided project brief with audience, type, experience, and constraints
- MVP-oriented project summary and five-step build sequence
- Suggested technology stack based on project type and idea keywords
- Draft README, TypeScript project brief, and HTML landing page
- Copy individual starter files or download them together as a ZIP
- Local planning review that calls out assumptions and missing specificity
- Recent builds stored on the current device

## Run it

No build tools or package installation are required.

1. Clone or download this repository.
2. Open `index.html` in a modern browser.

You can also serve the folder with any static web server. For example:

```sh
python3 -m http.server 8000
```

Then visit `http://localhost:8000`.

## How it works

The current version uses deterministic browser-side rules and templates. It selects a suggested stack from the chosen project type and a few idea keywords, then builds a generic sequence for narrowing scope, mapping a user journey, implementing a happy path, adding persistence and recovery, and collecting user feedback. The review panel checks basic brief qualities and surfaces assumptions.

The app does not call an LLM, create or run a real application repository, execute generated code, or verify a stack against the user's environment. The generated files are starting drafts, not a finished application. The review is a planning checklist, not a security audit or test run.

## Privacy and storage

The project brief and saved builds stay in the browser's local storage. They are not sent to a server by this app. Clearing browser storage removes saved builds. The page uses Google Fonts when an internet connection is available; system fonts are used when they are not.

## Project files

```
.
├── index.html   # Self-contained app: markup, styling, and browser-side logic
└── README.md    # Project overview and usage guide
```

## Roadmap

- Improve scope extraction and make assumptions editable
- Add clearer per-project-type starter templates
- Let users edit and export a complete project folder
- Add optional model providers behind explicit user configuration
- Add stronger validation for generated artifacts

## Contributing

Issues and pull requests are welcome. For behavior changes, include a short reproduction or example brief and describe the expected result. Keep generated or sample output clearly labeled as draft until it has been verified.

## License

See [LICENSE](LICENSE).
