---
name: setup-pre-commit
description: Configures Husky pre-commit hooks with lint-staged (Prettier), type checking, and tests in the current repository. Use when the user wants to add pre-commit hooks, set up Husky,
  configure lint-staged, or wire formatting/type-checking/tests into the commit step.
---

# Pre-Commit Hook Setup

## What gets configured

- **Husky** pre-commit hook
- **lint-staged** running Prettier on all staged files
- **Prettier** configuration (if not present)
- **typecheck** and **test** scripts in the pre-commit hook

## Steps

### 1. Detect the package manager

Check for `package-lock.json` (npm), `pnpm-lock.yaml` (pnpm), `yarn.lock` (yarn), `bun.lockb` (bun). Use whichever is found. Default to npm if unclear.

### 2. Install dependencies

Install as devDependencies:

```
husky lint-staged prettier
```

### 3. Initialize Husky

```bash
npx husky init
```

This creates the `.husky/` directory and adds `prepare: "husky"` to package.json.

### 4. Create `.husky/pre-commit`

Write this file (Husky v9+ does not need a shebang):

```
npx lint-staged
npm run typecheck
npm run test
```

**Adapt**: replace `npm` with the detected package manager. If package.json has no `typecheck` or `test` script, drop the corresponding line and inform the user.

### 5. Create `.lintstagedrc`

```json
{
  "*": "prettier --ignore-unknown --write"
}
```

### 6. Create `.prettierrc` (if missing)

Create only if no Prettier configuration exists yet. Use these defaults:

```json
{
  "useTabs": false,
  "tabWidth": 2,
  "printWidth": 80,
  "singleQuote": false,
  "trailingComma": "es5",
  "semi": true,
  "arrowParens": "always"
}
```

### 7. Verify

- [ ] `.husky/pre-commit` exists and is executable
- [ ] `.lintstagedrc` exists
- [ ] The `prepare` script in package.json equals `"husky"`
- [ ] A `prettier` configuration exists
- [ ] Run `npx lint-staged` to confirm everything works

### 8. Commit

Stage all changed/created files and commit with the message: `Add pre-commit hooks (husky + lint-staged + prettier)`

This runs the changes through the new pre-commit hooks — a good smoke test that everything works.

## Notes

- Husky v9+ does not require a shebang in hook files
- `prettier --ignore-unknown` skips files Prettier cannot parse (images, etc.)
- The pre-commit hook first runs lint-staged (fast, only staged files), then full typecheck and tests
