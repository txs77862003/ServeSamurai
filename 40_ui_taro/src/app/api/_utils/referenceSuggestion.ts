import path from 'path';
import fs from 'fs/promises';
import fsSync from 'fs';

export type ReferenceSuggestion = {
  player: string;
  clipName: string;
  csvPath: string;
  csvPathRelative: string;
  previewImagePath?: string;
  frameDirRelative?: string;
  slug: string;
};

const IMAGE_EXTENSIONS = new Set(['.jpg', '.jpeg', '.png']);

async function directoryExists(target: string): Promise<boolean> {
  try {
    const stat = await fs.stat(target);
    return stat.isDirectory();
  } catch {
    return false;
  }
}

async function fileExists(target: string): Promise<boolean> {
  try {
    await fs.access(target);
    return true;
  } catch {
    return false;
  }
}

async function collectClipDirectories(root: string, maxDepth = 6): Promise<string[]> {
  const queue: Array<{ dir: string; depth: number }> = [{ dir: root, depth: 0 }];
  const visited = new Set<string>();
  const results: string[] = [];

  while (queue.length > 0) {
    const { dir, depth } = queue.shift()!;
    if (visited.has(dir)) {
      continue;
    }
    visited.add(dir);

    let entries: fsSync.Dirent[];
    try {
      entries = await fs.readdir(dir, { withFileTypes: true });
    } catch {
      continue;
    }

    const hasCsv = entries.some((entry) => !entry.isDirectory() && entry.name === 'keypoints_with_tracks.csv');
    if (hasCsv) {
      results.push(dir);
      continue;
    }

    if (depth >= maxDepth) {
      continue;
    }

    for (const entry of entries) {
      if (entry.isDirectory()) {
        queue.push({ dir: path.join(dir, entry.name), depth: depth + 1 });
      }
    }
  }

  return results.sort();
}

async function findFirstImage(frameDir: string): Promise<string | null> {
  let entries: fsSync.Dirent[];
  try {
    entries = await fs.readdir(frameDir, { withFileTypes: true });
  } catch {
    return null;
  }

  const images = entries
    .filter((entry) => entry.isFile() && IMAGE_EXTENSIONS.has(path.extname(entry.name).toLowerCase()))
    .map((entry) => entry.name)
    .sort();

  if (images.length === 0) {
    return null;
  }

  return path.join(frameDir, images[0]);
}

async function ensurePreviewCopy(source: string, destDir: string, destName: string): Promise<string | null> {
  try {
    await fs.mkdir(destDir, { recursive: true });
    const destination = path.join(destDir, destName);

    try {
      const [srcStat, dstStat] = await Promise.all([
        fs.stat(source),
        fs.stat(destination).catch(() => null),
      ]);

      if (!dstStat || srcStat.mtimeMs > dstStat.mtimeMs) {
        await fs.copyFile(source, destination);
      }
    } catch {
      await fs.copyFile(source, destination);
    }

    return destination;
  } catch {
    return null;
  }
}

function toPosixRelative(projectRoot: string, absolutePath: string): string {
  const relative = path.relative(projectRoot, absolutePath);
  return relative.split(path.sep).join('/');
}

export function makeSlug(player: string, clipName: string): string {
  return `${player}_${clipName}`.replace(/[^a-zA-Z0-9._-]/g, '_');
}

export async function buildReferenceSuggestions(
  player: string,
  projectRoot: string,
  publicDir: string,
): Promise<ReferenceSuggestion[]> {
  const searchRoots = [
    path.join(projectRoot, 'pose_tracks', 'players', player),
    path.join(projectRoot, 'pose_tracks', 'Cleaned_Data', 'players', player),
  ];

  const clipDirs: string[] = [];
  for (const root of searchRoots) {
    if (!(await directoryExists(root))) {
      continue;
    }
    const found = await collectClipDirectories(root, 6);
    clipDirs.push(...found);
  }

  const uniqueClipDirs = Array.from(new Set(clipDirs));
  const suggestions: ReferenceSuggestion[] = [];

  for (const clipDir of uniqueClipDirs) {
    const csvPath = path.join(clipDir, 'keypoints_with_tracks.csv');
    if (!(await fileExists(csvPath))) {
      continue;
    }

    const clipName = path.basename(clipDir);
    const slug = makeSlug(player, clipName);

    const frameDirCandidates = [
      path.join(projectRoot, 'frames', 'Cleaned_Data', 'players', player, clipName),
      path.join(projectRoot, 'frames', 'players', player, clipName),
    ];

    let previewImagePath: string | undefined;
    let frameDirRelative: string | undefined;

    for (const frameDir of frameDirCandidates) {
      if (!(await directoryExists(frameDir))) {
        continue;
      }
      const firstImage = await findFirstImage(frameDir);
      if (!firstImage) {
        continue;
      }

      const ext = path.extname(firstImage).toLowerCase();
      const sanitizedName = `${slug}_preview${ext}`;
      const copied = await ensurePreviewCopy(firstImage, publicDir, sanitizedName);
      if (copied) {
        previewImagePath = `/pose-reference/${sanitizedName}`;
      }
      frameDirRelative = toPosixRelative(projectRoot, frameDir);
      break;
    }

    suggestions.push({
      player,
      clipName,
      csvPath,
      csvPathRelative: toPosixRelative(projectRoot, csvPath),
      previewImagePath,
      frameDirRelative,
      slug,
    });
  }

  return suggestions;
}
