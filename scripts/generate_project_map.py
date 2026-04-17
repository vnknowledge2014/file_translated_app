import os
import json
import ast

# --- Config ---
ROOT_DIR = "."
GRAPH_FILE = ".omni/knowledge-graph.json"
OUTPUT_FILE = "PROJECT_MAP.md"

EXCLUDE_DIRS = {".agent", ".git", "__pycache__", "venv", "data", ".pytest_cache", ".omni", "scripts"}
EXCLUDE_FILES = {"AGENTS.md", "omni.config.yaml", "translation_cache.db"}
EXCLUDE_EXTS = {".pyc", ".db", ".png", ".jpg", ".patch", ".so"}

def should_process(filepath):
    path_parts = filepath.split(os.sep)
    for excl in EXCLUDE_DIRS:
        if excl in path_parts:
            return False
            
    filename = os.path.basename(filepath)
    if filename in EXCLUDE_FILES:
        return False
        
    _, ext = os.path.splitext(filename)
    if ext in EXCLUDE_EXTS:
        return False
        
    return True

def extract_python_metadata(filepath):
    """Extracts classes, functions, and module docstring from a Python file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            
        tree = ast.parse(content)
        docstring = ast.get_docstring(tree) or ""
        
        classes = []
        functions = []
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, ast.FunctionDef):
                functions.append(node.name)
                
        return {
            "docstring": docstring.split("\n")[0] if docstring else "", # First line only
            "classes": classes[:5], # Limit to 5
            "functions": functions[:5] # Limit to 5
        }
    except Exception:
        return None

def parse_graph(graph_json_path):
    deps = {}
    if not os.path.exists(graph_json_path):
        return deps
        
    with open(graph_json_path, 'r', encoding='utf-8') as f:
        graph = json.load(f)
        
    nodes = {node["id"]: node for node in graph.get("nodes", [])}
    
    for edge in graph.get("edges", []):
        source = edge.get("source")
        target = edge.get("target")
        rel = edge.get("type")
        
        if source in nodes and target in nodes:
            src_node = nodes[source]
            tgt_node = nodes[target]
            
            if src_node["type"] == "FILE" and tgt_node["type"] == "FILE":
                src_path = src_node.get("properties", {}).get("path")
                tgt_path = tgt_node.get("properties", {}).get("path")
                
                if src_path and tgt_path and src_path != tgt_path:
                    if src_path not in deps:
                        deps[src_path] = set()
                    deps[src_path].add((tgt_path, rel))
                    
    return deps

def filepath_matches(fp1, fp2):
    return fp1.replace("\\", "/").strip("./") == fp2.replace("\\", "/").strip("./")

def main():
    print("Parsing AST Knowledge Graph...")
    deps_map = parse_graph(GRAPH_FILE)
    
    print("Discovering files...")
    files_to_process = []
    for root, dirs, files in os.walk(ROOT_DIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in files:
            filepath = os.path.normpath(os.path.join(root, f))
            if should_process(filepath):
                files_to_process.append(filepath)
                
    files_to_process.sort()
    print(f"Found {len(files_to_process)} files to analyze.")
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        out.write("# Project Map (Agent-Friendly Context)\n\n")
        out.write("> This document provides semantic summaries, structural metadata, and dependency relationships for all core project files.\n\n")
        
        # Group files logically
        backend_files = [f for f in files_to_process if f.startswith("backend/app")]
        test_files = [f for f in files_to_process if f.startswith("backend/tests")]
        other_files = [f for f in files_to_process if f not in backend_files and f not in test_files]
        
        sections = [
            ("## 1. Core Application (backend/app)", backend_files),
            ("## 2. Tests (backend/tests)", test_files),
            ("## 3. Configuration & Root", other_files)
        ]
        
        for section_title, file_group in sections:
            if not file_group:
                continue
            out.write(f"{section_title}\n\n")
            
            for fp in file_group:
                out.write(f"### `{fp}`\n")
                
                # Metadata
                if fp.endswith(".py"):
                    meta = extract_python_metadata(fp)
                    if meta:
                        out.write(f"- **Purpose:** {meta['docstring'] or 'No docstring provided.'}\n")
                        if meta['classes']:
                            out.write(f"- **Classes:** {', '.join(meta['classes'])}\n")
                        if meta['functions']:
                            out.write(f"- **Functions:** {', '.join(meta['functions'])}\n")
                else:
                    out.write(f"- **Type:** Non-Python resource/config file.\n")
                
                # Dependencies
                normalized_fp = fp.lstrip("./")
                file_deps = [tgt for known_src, targets in deps_map.items() 
                            if filepath_matches(normalized_fp, known_src) 
                            for tgt, rel in targets]
                
                if file_deps:
                    out.write(f"- **Calls/Imports:** ")
                    deps_list = sorted(set(file_deps))
                    formatted_deps = []
                    for d in deps_list:
                        # Clean up paths for readability relative to backend/app
                        clean_d = d.replace("backend/app/", "")
                        formatted_deps.append(f"`{clean_d}`")
                    out.write(", ".join(formatted_deps) + "\n")
                
                out.write("\n")

    print(f"Successfully wrote {OUTPUT_FILE}!")

if __name__ == "__main__":
    main()
