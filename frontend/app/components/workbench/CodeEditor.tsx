import { useStore } from "@nanostores/react";
import { useRef, useEffect } from "react";
import { EditorView, keymap, lineNumbers, highlightActiveLineGutter, highlightSpecialChars, drawSelection, highlightActiveLine, rectangularSelection, crosshairCursor, dropCursor } from "@codemirror/view";
import { EditorState, Compartment } from "@codemirror/state";
import { defaultKeymap, history, historyKeymap } from "@codemirror/commands";
import { syntaxHighlighting, defaultHighlightStyle, bracketMatching, foldGutter, indentOnInput } from "@codemirror/language";
import { closeBrackets, closeBracketsKeymap } from "@codemirror/autocomplete";
import { highlightSelectionMatches, searchKeymap } from "@codemirror/search";
import { oneDark } from "@codemirror/theme-one-dark";
import { javascript } from "@codemirror/lang-javascript";
import { python } from "@codemirror/lang-python";
import { json } from "@codemirror/lang-json";
import { html } from "@codemirror/lang-html";
import { css } from "@codemirror/lang-css";
import { $fileMap, $activeFile } from "../../stores/files";
import { $agentState } from "../../stores/agent";

function getLanguageExtension(filename: string) {
  const ext = filename.split(".").pop()?.toLowerCase();
  switch (ext) {
    case "js":
      return javascript();
    case "jsx":
      return javascript({ jsx: true });
    case "ts":
      return javascript({ typescript: true });
    case "tsx":
      return javascript({ jsx: true, typescript: true });
    case "py":
      return python();
    case "json":
      return json();
    case "html":
      return html();
    case "css":
      return css();
    default:
      return null;
  }
}

const basicSetup = [
  lineNumbers(),
  highlightActiveLineGutter(),
  highlightSpecialChars(),
  history(),
  foldGutter(),
  drawSelection(),
  dropCursor(),
  EditorState.allowMultipleSelections.of(true),
  indentOnInput(),
  syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
  bracketMatching(),
  closeBrackets(),
  rectangularSelection(),
  crosshairCursor(),
  highlightActiveLine(),
  highlightSelectionMatches(),
  keymap.of([
    ...closeBracketsKeymap,
    ...defaultKeymap,
    ...searchKeymap,
    ...historyKeymap,
  ]),
];

export default function CodeEditor() {
  const fileMap = useStore($fileMap);
  const activeFile = useStore($activeFile);
  const agentState = useStore($agentState);
  const containerRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);
  const languageCompartment = useRef(new Compartment());
  const readOnlyCompartment = useRef(new Compartment());

  const content = activeFile ? fileMap[activeFile]?.content ?? "" : "";
  const isReadOnly = agentState === "running";

  // Create / recreate editor when active file changes
  useEffect(() => {
    if (!containerRef.current || !activeFile) return;

    // Destroy previous view
    if (viewRef.current) {
      viewRef.current.destroy();
      viewRef.current = null;
    }

    const langExt = getLanguageExtension(activeFile);
    const extensions = [
      basicSetup,
      oneDark,
      languageCompartment.current.of(langExt ? [langExt] : []),
      readOnlyCompartment.current.of(EditorState.readOnly.of(isReadOnly)),
      EditorView.theme({
        "&": { height: "100%" },
        ".cm-scroller": { overflow: "auto" },
      }),
    ];

    const state = EditorState.create({ doc: content, extensions });
    viewRef.current = new EditorView({ state, parent: containerRef.current });

    return () => {
      viewRef.current?.destroy();
      viewRef.current = null;
    };
    // Intentionally depend on activeFile to recreate editor on file switch
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeFile]);

  // Update content when file content changes (without recreating the editor)
  useEffect(() => {
    const view = viewRef.current;
    if (!view || !activeFile) return;

    const currentDoc = view.state.doc.toString();
    if (currentDoc !== content) {
      view.dispatch({
        changes: { from: 0, to: currentDoc.length, insert: content },
      });
    }
  }, [content, activeFile]);

  // Update read-only state
  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;
    view.dispatch({
      effects: readOnlyCompartment.current.reconfigure(EditorState.readOnly.of(isReadOnly)),
    });
  }, [isReadOnly]);

  return <div ref={containerRef} style={{ height: "100%", width: "100%" }} />;
}
