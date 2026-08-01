## How to Contribute

Contributing to the CatLINK v2 Custom Integration for Home Assistant is a great way to help improve the project, add new features, fix bugs, or enhance documentation. We welcome contributions from developers of all skill levels. Here's how you can get started:

### 1. Fork the Repository

Start by forking the repository on GitHub. This will create a copy of the project under your own GitHub account. You can make changes in this fork without affecting the original project.

- Go to the GitHub page for the CatLINK v2 Custom Integration.
- Click the "Fork" button in the top-right corner of the page.

### 2. Clone the Repository

Next, clone your forked repository to your local machine to begin working on it.

```shell
git clone https://github.com/your-username/catlink.git
cd catlink
```

### 3. Create a New Branch

Before making any changes, create a new branch. This keeps your changes organized and allows you to work on multiple features or fixes simultaneously.

```shell
git checkout -b your-branch-name
```

### 4. Make Your Changes

Now you can start coding! Make your desired changes to the codebase, whether it's adding a new feature, fixing a bug, or improving the documentation.

- Ensure your code follows the existing style and conventions.
- If you are adding a new feature, consider writing tests to ensure it works as expected.

#### Running a local Home Assistant for development

The repository ships a Docker Compose stack that boots a throwaway Home
Assistant instance with this integration bind-mounted from your working tree.

```shell
docker compose up -d          # start; the first boot takes a minute
open http://localhost:8123    # onboard with any throwaway account
```

Then add the integration from **Settings → Devices & Services → Add
Integration → CatLink**.

| Command | What it does |
| --- | --- |
| `docker compose logs -f` | Follow logs — `custom_components.catlink` is set to `DEBUG` |
| `docker compose restart` | Reload after editing Python (see the note below) |
| `docker compose up -d --build` | Rebuild after changing `manifest.json` requirements |
| `docker compose down` | Stop, keeping the Home Assistant config |
| `docker compose down -v && rm -rf dev/ha-config/.storage` | Full reset back to onboarding |

The stack builds a thin layer over the official image ([dev/Dockerfile](dev/Dockerfile))
that pre-installs the `manifest.json` requirements. Home Assistant would
otherwise install them lazily on first use, and when that install does not
happen the only symptom is *"Invalid handler specified"* in the UI. Baking them
in makes startup deterministic — but it also means **a new entry in
`manifest.json` needs `--build`, not just a restart**.

Your edits are visible inside the container immediately, but Home Assistant
imports the Python modules once at startup — **restart the container for code
changes to take effect**. Changes to `translations/*.json` also need a restart.

Pin a specific core version when you need to reproduce a version-specific bug:

```shell
HA_VERSION=2026.7 docker compose up -d
```

#### Attaching a debugger

The stack enables Home Assistant's `debugpy` integration on port `5678`. In
VS Code, run the bundled **"Attach to Home Assistant (Docker)"** launch
configuration and set breakpoints anywhere under `custom_components/catlink`.
Startup does not block waiting for a debugger, so you can attach and detach at
any time.

#### A note on translations

Custom integrations do not run Home Assistant's translation build script, so
`strings.json` alone is never read at runtime — the UI falls back to raw keys.
Any string you add to `strings.json` must also be added to
`custom_components/catlink/translations/en.json`, which is the file Home
Assistant actually loads. Keep the two in sync.

Other languages live alongside it as `translations/<code>.json` (currently
`it.json`). They must mirror the exact key structure of `en.json`; Home
Assistant falls back to English for any key a translation omits.

### 5. Commit Your Changes

Once your changes are ready, commit them to your branch.

```shell
git add .
git commit -m "Description of the changes"
```

### 6. Push to Your Fork

Push your changes to your forked repository on GitHub.

```shell
git push origin your-branch-name
```

### 7. Create a Pull Request

Finally, navigate to the original repository on GitHub and create a pull request (PR). This will submit your changes for review and potential inclusion in the main project.

- Go to the "Pull Requests" section of the original repository.
- Click "New Pull Request" and select your branch.
- Provide a detailed description of your changes and any relevant information.

### 8. Participate in the Review Process

Your pull request will be reviewed by the project maintainers. Be prepared to make additional changes based on their feedback. The review process is collaborative, and maintainers may suggest improvements to your code or ask questions about your implementation.

### 9. Celebrate Your Contribution

Once your pull request is merged, congratulations! You've successfully contributed to the CatLINK v2 Custom Integration for Home Assistant. Your work is now part of the project and will benefit users worldwide.

---

### Code of Conduct

Please ensure that you follow our [Code of Conduct](#) when contributing to the project. We are committed to maintaining a welcoming and inclusive environment for all contributors.

---

This segment guides contributors through the process of making contributions to the CatLINK v2 Custom Integration, from forking the repository to creating a pull request and getting their code merged into the project.
