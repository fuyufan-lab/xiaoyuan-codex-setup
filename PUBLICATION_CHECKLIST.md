# Publication Checklist

Run this before publishing changes to the public bootstrap repository.

```bash
bash scripts/publication_guard.sh
```

The public repository may contain only docs, safe manifest metadata, the guard script, and the explicit client-only bridge files listed above.

Do not publish changes unless this checklist passes from a clean worktree.
