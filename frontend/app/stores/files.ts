import { atom, computed } from "nanostores";
import type { FileNode, TreeNode } from "../lib/types";

export const $fileMap = atom<Record<string, FileNode>>({});
export const $activeFile = atom<string | null>(null);

export function setFile(path: string, content: string) {
  const map = { ...$fileMap.get() };
  map[path] = { path, content, locked: false, lastModified: new Date().toISOString() };
  $fileMap.set(map);
  // Auto-select first file
  if (!$activeFile.get()) $activeFile.set(path);
}

export function editFile(path: string, oldStr: string, newStr: string) {
  const map = { ...$fileMap.get() };
  const file = map[path];
  if (file) {
    // Intentionally replaces only the first occurrence (matches backend edit_file / str_replace behavior)
    map[path] = { ...file, content: file.content.replace(oldStr, newStr), lastModified: new Date().toISOString() };
    $fileMap.set(map);
  }
}

// Build tree from flat file map
export const $fileTree = computed($fileMap, (fileMap) => {
  const root: TreeNode[] = [];
  const paths = Object.keys(fileMap).sort();

  for (const path of paths) {
    const parts = path.split("/").filter(Boolean);
    let current = root;

    for (let i = 0; i < parts.length; i++) {
      const name = parts[i];
      const fullPath = parts.slice(0, i + 1).join("/");
      const isFile = i === parts.length - 1;

      let node = current.find((n) => n.name === name);
      if (!node) {
        node = { name, path: fullPath, type: isFile ? "file" : "directory", children: isFile ? undefined : [] };
        current.push(node);
      }
      if (!isFile && node.children) {
        current = node.children;
      }
    }
  }
  return root;
});
