import path from 'path';
import fs from 'fs';

/**
 * Resolve the repository root (the directory above the Next.js app).
 */
export function getProjectRoot(): string {
  return path.resolve(process.cwd(), '..');
}

/**
 * Pick a Python executable, preferring local virtual environments when available.
 */
export function resolvePythonCommand(): string {
  const candidates = [
    path.resolve(process.cwd(), '..', '.venv', 'bin', 'python'),
    path.resolve(process.cwd(), '..', 'venv', 'bin', 'python'),
    'python3',
  ];

  for (const candidate of candidates) {
    if (candidate === 'python3') {
      return candidate;
    }
    try {
      fs.accessSync(candidate, fs.constants.X_OK);
      return candidate;
    } catch {
      /* try next candidate */
    }
  }

  return 'python3';
}
