#!/usr/bin/env python3
import os
import sys
import subprocess

def main():
    workspace_dir = os.path.dirname(os.path.abspath(__file__))
    electron_app_dir = os.path.join(workspace_dir, "electron_app")
    
    # Locate NVM Node version dynamically to inject into PATH
    env = os.environ.copy()
    nvm_node_dir = os.path.expanduser("~/.nvm/versions/node")
    if os.path.exists(nvm_node_dir):
        versions = sorted(os.listdir(nvm_node_dir))
        # Filter out hidden files
        versions = [v for v in versions if not v.startswith('.')]
        if versions:
            latest_version = versions[-1]
            node_bin_dir = os.path.join(nvm_node_dir, latest_version, "bin")
            if os.path.exists(node_bin_dir):
                env["PATH"] = node_bin_dir + os.pathsep + env.get("PATH", "")
                print(f"[Launcher] Using Node version {latest_version} via NVM path.")
                
    print("=== Launching Kruboo AI Assistant (Electron) ===")
    
    try:
        # Run Electron app using npm start with the updated PATH env
        subprocess.run(["npm", "start"], cwd=electron_app_dir, env=env)
    except KeyboardInterrupt:
        print("\nShutdown complete.")

if __name__ == "__main__":
    main()
